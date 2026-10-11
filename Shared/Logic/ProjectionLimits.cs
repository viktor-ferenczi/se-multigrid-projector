using System.Collections.Generic;
using System.Linq;
using MultigridProjector.Config;
using MultigridProjector.Extensions;
using MultigridProjector.Utilities;
using Sandbox.Game;
using Sandbox.Game.Entities.Blocks;
using Sandbox.Game.Multiplayer;
using Sandbox.Game.World;
using VRage.Game;

namespace MultigridProjector.Logic
{
    // Server-side limit on the PCU of the projections a player loads (GitHub issue #86).
    //
    // The PCU of the player's blocks, of their projections and of the new projection together may be
    // at most ProjectionPcuLimitPercent of the player's PCU limit. A projection's PCU counts from the
    // moment it is accepted until the projector stops projecting it. The player is the one who built
    // the projector, the same identity the game checks for its own projections.
    //
    // The count is kept here, not in the player's PCU: a repair projection would otherwise use up the
    // PCU needed to weld the blocks it is for. With the limit off (0, the default) the plugin neither
    // checks nor counts projections, and the game's own projection check is skipped for the
    // projectors the plugin handles.
    public static class ProjectionLimits
    {
        // Projector entity ID => (identity of the player, PCU of the projection). Game thread only.
        private static readonly Dictionary<long, (long IdentityId, long Pcu)> Reserved =
            new Dictionary<long, (long, long)>();

        private static int LimitPercent => PluginConfig.Current.ProjectionPcuLimitPercent;

        // The projectors MGP handles, the same condition as for creating a multigrid projection
        public static bool IsHandled(MyProjectorBase projector)
        {
            return projector.AllowWelding && !projector.AllowScaling;
        }

        // Called right before the projector activates its clipboard. False refuses the projection,
        // the projector must not activate it then.
        [Everywhere]
        public static bool TryReserve(MyProjectorBase projector)
        {
            // Only the server decides, a client always accepts and gets the projection removed if refused
            if (!Sync.IsServer || LimitPercent <= 0 || !IsHandled(projector))
                return true;

            var clipboard = projector.GetClipboard();
            if (!clipboard.HasCopiedGrids() || clipboard.IsActive || projector.IsActivating)
                return true;

            if (MySession.Static.BlockLimitsEnabled == MyBlockLimitsEnabledEnum.NONE)
                return true;

            var identity = MySession.Static.Players.TryGetIdentity(projector.BuiltBy);
            if (identity == null || IgnoresPcuLimit(identity.IdentityId))
                return true;

            clipboard.CopiedGrids.TryCalculatePcu(out var pcu, out _);

            var otherProjections = Reserved
                .Where(p =>
                    p.Key != projector.EntityId && p.Value.IdentityId == identity.IdentityId
                )
                .Sum(p => p.Value.Pcu);
            var total = identity.BlockLimits.PCUBuilt + otherProjections + pcu;

            var allowed = (long)MyBlockLimits.GetMaxPCU(identity) * LimitPercent / 100;
            if (total > allowed)
            {
                Refuse(projector, identity.IdentityId, pcu, total, allowed);
                return false;
            }

            Reserved[projector.EntityId] = (identity.IdentityId, pcu);

            return true;
        }

        // Called after the projector stopped projecting
        [Everywhere]
        public static void Release(MyProjectorBase projector)
        {
            Reserved.Remove(projector.EntityId);
        }

        public static void Clear()
        {
            Reserved.Clear();
        }

        // Admins with the "Ignore PCU limits" admin setting, as the game checks them
        private static bool IgnoresPcuLimit(long identityId)
        {
            var steamId = MySession.Static.Players.TryGetSteamId(identityId);
            return steamId != 0
                && MySession.Static.RemoteAdminSettings.TryGetValue(steamId, out var settings)
                && (settings & AdminSettingsEnum.IgnorePcu) != 0;
        }

        private static void Refuse(
            MyProjectorBase projector,
            long identityId,
            long pcu,
            long total,
            long allowed
        )
        {
            PluginLog.Info(
                $"Refused a projection of {pcu} PCU on projector \"{projector.CustomName}\" [{projector.EntityId}]: the player's blocks and projections would take {total} PCU, the projection limit is {allowed} PCU"
            );

            MyVisualScriptLogicProvider.ShowNotification(
                $"Projection refused: with its {pcu} PCU your blocks and projections would take {total} PCU, over the projection limit of {allowed} PCU",
                10000,
                "Red",
                identityId
            );

            // Take it away from the clients as well. On the next frame, so a client which receives
            // the new blueprint from this server removes it after that.
            Events.InvokeOnGameThread(
                () =>
                {
                    if (!projector.Closed)
                        projector.SendRemoveProjection();
                },
                1
            );
        }

        // Replaces the identity lookup of the game's own projection PCU count in MyProjectorBase
        // (see MyProjectorBase_GameProjectionPcu). Without an identity the game skips it.
        public static MyIdentity IdentityForGameCheck(
            MyPlayerCollection players,
            long identityId,
            MyProjectorBase projector
        )
        {
            return IsHandled(projector) ? null : players.TryGetIdentity(identityId);
        }
    }
}
