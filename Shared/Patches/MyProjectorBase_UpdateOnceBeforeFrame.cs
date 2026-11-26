using HarmonyLib;
using MultigridProjector.Utilities;
using Sandbox.Game.Entities.Blocks;
using Sandbox.Game.Multiplayer;

namespace MultigridProjector.Patches
{
    /* MGP's Init postfix sets m_originalGridBuilders to the saved projection, the same list the
       game keeps in m_savedProjections. On the server that makes OnRegisteredToGridSystems run
       Remap, which loads the blueprint into the clipboard, so the projection gets built as soon
       as the projector has power. Then the game's UpdateOnceBeforeFrame loads m_savedProjections
       again: it replaces the clipboard's grids and builds the projection a second time. For a big
       blueprint each build costs a long frame, on every world load and every cluster handover of
       the grid (SE-1942).

       The blueprint is already in the clipboard then, so the game's second load is dropped.
       Saving still works: GetObjectBuilderCubeBlock uses m_originalGridBuilders while the
       clipboard has grids. */

    // ReSharper disable once UnusedType.Global
    [HarmonyPatch(typeof(MyProjectorBase))]
    [HarmonyPatch("UpdateOnceBeforeFrame")]
    [EnsureOriginal("49ec6cdb")]
    // ReSharper disable once InconsistentNaming
    public static class MyProjectorBase_UpdateOnceBeforeFrame
    {
        [Everywhere]
        // ReSharper disable once UnusedMember.Local
        private static void Prefix(MyProjectorBase __instance)
        {
            var projector = __instance;
            var saved = projector.m_savedProjections;
            if (saved == null || !Sync.IsServer || projector.CubeGrid?.Physics == null)
                return;

            var clipboard = projector.m_clipboard;
            if (
                !ReferenceEquals(projector.m_originalGridBuilders, saved)
                || clipboard?.CopiedGrids == null
                || clipboard.CopiedGrids.Count != saved.Count
            )
                return;

            projector.m_savedProjections = null;
        }
    }
}
