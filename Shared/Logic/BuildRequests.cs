using System;
using System.Collections.Generic;
using System.Diagnostics;
using MultigridProjector.Utilities;
using Sandbox.Game.World;
using VRage.Game;
using VRage.Network;
using VRageMath;

namespace MultigridProjector.Logic
{
    // The server side of the full mode build requests a client sends as mod messages (see Comms).
    //
    // Building from here is a local call as far as the game is concerned, so guards on the vanilla
    // BuildInternal RPC (like Anti-Cheat's) don't see it. The checks of such a guard are here
    // instead: the player builds only as themselves, with their own character, within reach and
    // at a sane rate. The projector's own checks (welding allowed, DLC, block buildable in the
    // server's state) are in MultigridProjection.BuildInternal, which runs in an event context of
    // the sender, exactly as for a vanilla RPC.
    public static class BuildRequests
    {
        // Anti-Cheat allows 3 times the interactive distance; a hand welder reaches a few meters
        private static readonly double MaxReachSquared = Math.Pow(
            MyConstants.DEFAULT_INTERACTIVE_DISTANCE * 3,
            2
        );

        // A hand welder asks for a few blocks a second
        private const int MaxBuildRequestsPerSecond = 20;

        private static readonly Stopwatch Clock = Stopwatch.StartNew();
        private static readonly BuildRateLimit RateLimit = new BuildRateLimit();
        private static readonly HashSet<string> Logged = new HashSet<string>();

        [ServerOnly]
        public static void Handle(ulong sender, BuildRequest request)
        {
            LogOnce(sender, "mod message", $"Build requests from {sender} arrive as mod messages");

            if (
                !MultigridProjection.TryFindProjectionByProjector(
                    request.ProjectorId,
                    out var projection
                )
            )
            {
                Refuse(sender, "no multigrid projection", request);
                return;
            }

            var players = MySession.Static.Players;
            var identityId = players.TryGetIdentityId(sender);
            var character = players.TryGetIdentity(identityId)?.Character;
            if (
                identityId == 0
                || request.Owner != identityId
                || character == null
                || character.EntityId != request.Builder
                || players
                    .GetPlayerById(new MyPlayer.PlayerId(sender))
                    ?.Controller?.ControlledEntity != character
            )
            {
                Refuse(sender, "not the sender's own identity and controlled character", request);
                return;
            }

            if (!projection.TryGetSupportedSubgrid(request.SubgridIndex, out var subgrid))
            {
                Refuse(sender, "no such subgrid", request);
                return;
            }

            var position = new Vector3I(request.X, request.Y, request.Z);
            var creative =
                MySession.Static.CreativeMode || MySession.Static.HasPlayerCreativeRights(sender);
            if (!creative)
            {
                var previewBlock = subgrid.PreviewGrid?.GetCubeBlock(position);
                if (previewBlock == null)
                {
                    Refuse(sender, "no such projected block", request);
                    return;
                }

                previewBlock.GetWorldBoundingBox(out var box);
                if (box.DistanceSquared(character.PositionComp.GetPosition()) > MaxReachSquared)
                {
                    Refuse(sender, "out of reach", request);
                    return;
                }

                if (!RateLimit.Allow(sender, Clock.Elapsed.TotalSeconds, MaxBuildRequestsPerSecond))
                {
                    Refuse(sender, "over the rate limit", request);
                    return;
                }
            }

            using (MyEventContext.Set(new EndpointId(sender), null, false))
                projection.BuildInternal(
                    position,
                    request.Owner,
                    request.Builder,
                    request.RequestInstant,
                    request.SubgridIndex
                );
        }

        // The sender checks of the vanilla BuildInternal RPC since 1.211.018: the builder is the
        // sender's own character, which the sender controls, and builtBy is the sender's identity.
        // MGP's own Build patches call BuildInternal locally, with the subgrid index in builtBy,
        // so this applies to RPCs from clients only.
        public static bool IsRpcAllowed(ulong sender, long builder, long builtBy)
        {
            var players = MySession.Static.Players;
            var player = players.GetPlayerById(new MyPlayer.PlayerId(sender));
            var character = player?.Character;
            if (
                character == null
                || character.EntityId != builder
                || player.Controller?.ControlledEntity != character
            )
            {
                LogOnce(
                    sender,
                    "rpc builder",
                    $"Refused a BuildInternal RPC from {sender}: builder {builder} is not the sender's controlled character"
                );
                return false;
            }

            var identityId = players.TryGetIdentityId(sender);
            if (identityId == 0 || builtBy != identityId)
            {
                LogOnce(
                    sender,
                    "rpc builtBy",
                    $"Refused a BuildInternal RPC from {sender}: builtBy {builtBy} is not the sender's identity {identityId}"
                );
                return false;
            }

            return true;
        }

        // A BuildInternal RPC from a client, for the record. Vanilla clients and MGP clients in
        // client-only mode send builtBy = owner.
        public static void NoteRpc(ulong sender, long owner, long builtBy)
        {
            LogOnce(
                sender,
                "rpc",
                builtBy == owner
                    ? $"BuildInternal RPC from {sender} with vanilla arguments"
                    : $"BuildInternal RPC from {sender} with builtBy {builtBy}, not the owner {owner}"
            );
        }

        private static void Refuse(ulong sender, string reason, BuildRequest request)
        {
            LogOnce(
                sender,
                reason,
                $"Refused a build request from {sender}: {reason} (projector {request.ProjectorId}, subgrid {request.SubgridIndex}, block {request.X},{request.Y},{request.Z})"
            );
        }

        public static void LogOnce(ulong sender, string kind, string message)
        {
            lock (Logged)
                if (!Logged.Add($"{sender} {kind}"))
                    return;

            PluginLog.Info(message);
        }
    }
}
