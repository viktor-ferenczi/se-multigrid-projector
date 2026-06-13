using System.Runtime.CompilerServices;
using Sandbox.Game.Entities;
using Sandbox.Game.Entities.Blocks;
using Sandbox.Game.Entities.Cube;
using System.Collections.Generic;
using System.Linq;
using Sandbox.Game.Screens.Helpers;
using Sandbox.ModAPI;
using SpaceEngineers.Game.Entities.Blocks;
using VRage.Game;
using VRage.ObjectBuilder;
using VRage.Sync;
using VRageMath;

namespace MultigridProjector.Extensions
{
    public static class MyCubeBlockExtensions
    {
        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        public static string GetSafeName(this MyCubeBlock block)
        {
            return block?.DisplayNameText ?? block?.DisplayName ?? block?.Name ?? "";
        }

        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        public static string GetDebugName(this MyCubeBlock block)
        {
            return $"{block.GetSafeName()} [{block.EntityId}]";
        }

        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        public static bool HasSameDefinition(this MySlimBlock block, MySlimBlock other)
        {
            return block.BlockDefinition.Id == other.BlockDefinition.Id;
        }

        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        public static bool IsMatchingBuilder(this MySlimBlock previewBlock, MyObjectBuilder_CubeBlock blockBuilder)
        {
            return previewBlock.BlockDefinition.Id == blockBuilder.GetId() &&
                   previewBlock.Orientation.Forward == blockBuilder.BlockOrientation.Forward &&
                   previewBlock.Orientation.Up == blockBuilder.BlockOrientation.Up;
        }

        // RecreateTop is now public on MyMechanicalConnectionBlockBase (via the publicizer),
        // so callers invoke it directly without a reflection wrapper.

        // Aligns the grid of the block to a corresponding block on another grid
        public static void AlignGrid(this MyCubeBlock block, MyCubeBlock referenceBlock)
        {
            // Misaligned preview grid position and orientation
            var wm = block.CubeGrid.WorldMatrix;

            // Center the preview block
            wm.Translation -= block.WorldMatrix.Translation;

            // Reorient to match the built block
            wm *= MatrixD.Invert(block.PositionComp.GetOrientation());
            wm *= referenceBlock.PositionComp.GetOrientation();

            // Translate to the built block's position
            wm.Translation += referenceBlock.WorldMatrix.Translation;

            // Move the preview grid
            block.CubeGrid.PositionComp.SetWorldMatrix(ref wm, skipTeleportCheck: true);
        }

        public static List<MyCubeGrid> GetFocusedGridsInMechanicalGroup(this MyCubeBlock focusedBlock)
        {
            var physicalGroup = MyCubeGridGroups.Static.Physical.GetGroup(focusedBlock.CubeGrid);
            if (physicalGroup == null)
                return null;

            var grids = physicalGroup.Nodes.Select(node => node.NodeData).ToList();

            grids.Remove(focusedBlock.CubeGrid);
            grids.Insert(0, focusedBlock.CubeGrid);

            return grids;
        }

        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        public static MyToolbar GetToolbar(this MyTerminalBlock block)
        {
            switch (block)
            {
                case MySensorBlock b:
                    return b.Toolbar;
                case MyButtonPanel b:
                    return b.Toolbar;
                case MyEventControllerBlock b:
                    return b.Toolbar;
                case MyFlightMovementBlock b:
                    return b.Toolbar;
                case MyShipController b:
                    return b.Toolbar;
                case MyTimerBlock b:
                    return b.Toolbar;
                case MyDefensiveCombatBlock b:
                    return b.GetWaypointActionsToolbar();
                case MyOffensiveCombatBlock b:
                    return b.GetWaypointActionsToolbar();
            }

            return null;
        }

        public static MyToolbar GetWaypointActionsToolbar(this MyDefensiveCombatBlock defensiveCombatBlock)
        {
            return defensiveCombatBlock.m_waypointActionsToolbar;
        }

        public static MyToolbar GetWaypointActionsToolbar(this MyOffensiveCombatBlock offensiveCombatBlock)
        {
            return offensiveCombatBlock.m_waypointActionsToolbar;
        }

        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        public static Sync<long, SyncDirection.BothWays> GetBoundCameraSync(this MyRemoteControl remoteControlBlock)
        {
            return remoteControlBlock.m_bindedCamera /* sic */;
        }

        public static MySerializableList<long> GetSelectedBlockIds(this MyEventControllerBlock eventControllerBlock)
        {
            return eventControllerBlock.m_selectedBlockIds;
        }

        public static void SetSelectedBlockIds(this MyEventControllerBlock eventControllerBlock, MySerializableList<long> selectedBlockIds)
        {
            eventControllerBlock.m_selectedBlockIds = selectedBlockIds;
        }

        public static Dictionary<long, IMyTerminalBlock> GetSelectedBlocks(this MyEventControllerBlock eventControllerBlock)
        {
            return eventControllerBlock.m_selectedBlocks;
        }

        // SelectAvailableBlocks and SelectButton are now public on MyEventControllerBlock (via the
        // publicizer), so callers invoke them directly without reflection wrappers.
    }
}
