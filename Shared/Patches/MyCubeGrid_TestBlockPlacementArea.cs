using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using HarmonyLib;
using Havok;
using MultigridProjector.Utilities;
using Sandbox.Definitions;
using Sandbox.Game.Entities;
using Sandbox.Game.Entities.Cube;
using VRage.Game;
using VRageMath;

namespace MultigridProjector.Patches
{
    // Fixes a Havok shape leak in the game's block placement test (SE-1381).
    //
    // For a block whose model has no collision shapes and whose cube topology is not a
    // StandaloneBox, like armor blocks, MyCubeGrid.TestBlockPlacementArea builds fresh convex
    // shapes with MyCubeBlockCollector.AddConvexShape and wraps them into an HkListShape with
    // HkReferencePolicy.None. The list then holds a reference of its own on each child. Releasing
    // the list at the end drops only that one, so the children's own references leak: one or two
    // convex shapes on every call with Havok intersections. MGP's CanBuild(checkHavokIntersections:
    // true) calls it for every projected block in reach, Ship Welding many times a second, so a
    // client near a repair projection of a damaged ship ran out of Havok memory.
    //
    // The transpiler makes the list take over the children (TakeOwnership), as the game does
    // elsewhere for freshly made child shapes. The Bugfixes plugin fixes it too: whichever plugin
    // patches first changes the policy argument, the other one finds it changed and leaves it.
    //
    // ReSharper disable once UnusedType.Global
    [HarmonyPatch]
    // ReSharper disable once InconsistentNaming
    public static class MyCubeGrid_TestBlockPlacementArea
    {
        // ReSharper disable once UnusedMember.Local
        private static MethodBase TargetMethod() =>
            AccessTools
                .GetDeclaredMethods(typeof(MyCubeGrid))
                .Where(m => m.Name == nameof(MyCubeGrid.TestBlockPlacementArea))
                .OrderByDescending(m => m.GetParameters().Length)
                .First();

        [Everywhere]
        // ReSharper disable once UnusedMember.Global
        public static IEnumerable<CodeInstruction> Transpiler(
            IEnumerable<CodeInstruction> instructions
        )
        {
            var il = instructions.ToList();
            var addConvexShape = AccessTools.Method(
                typeof(MyCubeBlockCollector),
                nameof(MyCubeBlockCollector.AddConvexShape),
                new[]
                {
                    typeof(Vector3I),
                    typeof(Vector3I),
                    typeof(MyCubeBlockDefinition),
                    typeof(MyBlockOrientation),
                    typeof(float),
                    typeof(List<HkShape>),
                }
            );
            var listShape = AccessTools.Constructor(
                typeof(HkListShape),
                new[] { typeof(HkShape[]), typeof(int), typeof(HkReferencePolicy) }
            );

            var start = il.FindIndex(i => i.Calls(addConvexShape));
            var ctor =
                start < 0
                    ? -1
                    : il.FindIndex(
                        start,
                        i => i.opcode == OpCodes.Newobj && Equals(i.operand, listShape)
                    );
            var policy = ctor < 1 ? null : il[ctor - 1];

            if (policy == null)
                PluginLog.Warn(
                    "MyCubeGrid.TestBlockPlacementArea changed, the Havok shape leak fix is not applied"
                );
            else if (policy.opcode == OpCodes.Ldc_I4_1)
                policy.opcode = OpCodes.Ldc_I4_0; // HkReferencePolicy.TakeOwnership
            else
                PluginLog.Info(
                    "The Havok shape leak of MyCubeGrid.TestBlockPlacementArea is fixed by another plugin already"
                );

            return il;
        }
    }
}
