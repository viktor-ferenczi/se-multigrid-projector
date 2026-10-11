using System;
using HarmonyLib;
using MultigridProjector.Logic;
using MultigridProjector.Utilities;
using Sandbox.Game.Entities.Blocks;

namespace MultigridProjectorClient.Patches
{
    // ReSharper disable once UnusedType.Global
    [HarmonyPatch(typeof(MyProjectorBase))]
    [HarmonyPatch("InitializeClipboard")]
    [EnsureOriginal("dcf7ea34")]
    // ReSharper disable once InconsistentNaming
    public static class MyProjectorBase_InitializeClipboard
    {
        [ClientOnly]
        // ReSharper disable once UnusedMember.Local
        private static bool Prefix(
            // ReSharper disable once InconsistentNaming
            MyProjectorBase __instance
        )
        {
            var projector = __instance;

            // A new projection has no multigrid projection yet, the original implementation activates it
            // if the server's projection limit lets it
            if (!MultigridProjection.TryFindProjectionByProjector(projector, out var projection))
                return ProjectionLimits.TryReserve(projector);

#if DEBUG
            projection.InitializeClipboard();
#else
            try
            {
                projection.InitializeClipboard();
            }
            catch (Exception e)
            {
                PluginLog.Error(e);
            }
#endif

            return false;
        }
    }
}
