using System.Collections.Generic;
using System.Runtime.CompilerServices;
using Sandbox.Game.Entities;
using Sandbox.Game.Entities.Cube;
using Sandbox.Game.GameSystems;

namespace MultigridProjector.Extensions
{
    public static class MyCubeGridExtensions
    {
        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        public static string GetSafeName(this MyCubeGrid grid)
        {
            return grid?.DisplayNameText ?? grid?.DisplayName ?? grid?.Name ?? "";
        }

        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        public static string GetDebugName(this MyCubeGrid grid)
        {
            return $"{grid.GetSafeName()} [{grid.EntityId}]";
        }

        // RayCastBlocksAllOrdered and AddGroup are now public on MyCubeGrid (via the publicizer),
        // so callers invoke them directly without reflection wrappers.

        public static List<MyBlockGroup> GetBlockGroups(this MyCubeGrid grid)
        {
            return grid.BlockGroups;
        }

        [MethodImpl(MethodImplOptions.AggressiveInlining)]
        public static MySlimBlock GetOverlappingBlock(this MyCubeGrid grid, MySlimBlock block)
        {
            var cubeIndex = grid.WorldToGridInteger(block.WorldPosition);
            return grid.GetCubeBlock(cubeIndex);
        }
    }
}
