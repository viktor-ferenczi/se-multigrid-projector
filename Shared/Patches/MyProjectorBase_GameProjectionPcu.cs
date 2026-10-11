using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using HarmonyLib;
using MultigridProjector.Extensions;
using MultigridProjector.Logic;
using MultigridProjector.Utilities;
using Sandbox.Game.Entities.Blocks;
using Sandbox.Game.Multiplayer;

namespace MultigridProjector.Patches
{
    /* The game counts one PCU per block of a projection to the player who built the projector:
       it checks the player's limits and adds the PCU in InitializeClipboard, takes it off in
       RemoveProjection and moves it to the new grid in UpdateAfterSimulation. Each of them starts
       with the same identity lookup:

           MyIdentity myIdentity = MySession.Static.Players.TryGetIdentity(base.BuiltBy);
           if (myIdentity != null) { ... }

       For the projectors MGP handles these transpilers replace the lookup with one that returns
       null, so the game skips all three. ProjectionLimits counts these projections instead, if the
       server has a projection limit. MGP's own RemoveProjection never gave the PCU back, so before
       this the game's count only grew with every projection removed and loaded again. */
    public static class GameProjectionPcu
    {
        private static readonly MethodInfo TryGetIdentity = AccessTools.Method(
            typeof(MyPlayerCollection),
            nameof(MyPlayerCollection.TryGetIdentity)
        );
        private static readonly MethodInfo IdentityForGameCheck = AccessTools.Method(
            typeof(ProjectionLimits),
            nameof(ProjectionLimits.IdentityForGameCheck)
        );

        public static IEnumerable<CodeInstruction> Transpile(
            IEnumerable<CodeInstruction> instructions,
            MethodBase patchedMethod
        )
        {
            var il = instructions.ToList();
            il.RecordOriginalCode(patchedMethod);

            var i = il.FindIndex(ci => ci.Calls(TryGetIdentity));
            if (i < 0 || il.FindIndex(i + 1, ci => ci.Calls(TryGetIdentity)) >= 0)
                throw new CodeInstructionNotFound(
                    $"Expected exactly one call to TryGetIdentity in {patchedMethod.Name}"
                );

            il[i] = new CodeInstruction(OpCodes.Call, IdentityForGameCheck).MoveLabelsFrom(il[i]);
            il.Insert(i, new CodeInstruction(OpCodes.Ldarg_0));

            il.RecordPatchedCode(patchedMethod);
            return il.AsEnumerable();
        }
    }

    // ReSharper disable once UnusedType.Global
    [HarmonyPatch(typeof(MyProjectorBase))]
    [HarmonyPatch("InitializeClipboard")]
    [EnsureOriginal("dcf7ea34")]
    // ReSharper disable once InconsistentNaming
    public static class MyProjectorBase_InitializeClipboard_GamePcu
    {
        [Everywhere]
        public static IEnumerable<CodeInstruction> Transpiler(
            IEnumerable<CodeInstruction> instructions,
            MethodBase patchedMethod
        )
        {
            return GameProjectionPcu.Transpile(instructions, patchedMethod);
        }
    }

    // ReSharper disable once UnusedType.Global
    [HarmonyPatch(typeof(MyProjectorBase))]
    [HarmonyPatch("RemoveProjection")]
    [EnsureOriginal("b3568c13")]
    // ReSharper disable once InconsistentNaming
    public static class MyProjectorBase_RemoveProjection_GamePcu
    {
        [Everywhere]
        public static IEnumerable<CodeInstruction> Transpiler(
            IEnumerable<CodeInstruction> instructions,
            MethodBase patchedMethod
        )
        {
            return GameProjectionPcu.Transpile(instructions, patchedMethod);
        }

        // The projection's PCU counts as long as the projector projects it. MGP keeps projecting
        // when it is turned off (RemoveProjection with keepProjection), the game does not.
        [Everywhere]
        public static void Postfix(MyProjectorBase __instance)
        {
            if (!__instance.GetClipboard().IsActive)
                ProjectionLimits.Release(__instance);
        }
    }

    // ReSharper disable once UnusedType.Global
    [HarmonyPatch(typeof(MyProjectorBase))]
    [HarmonyPatch("UpdateAfterSimulation")]
    [EnsureOriginal("d844937e")]
    // ReSharper disable once InconsistentNaming
    public static class MyProjectorBase_UpdateAfterSimulation_GamePcu
    {
        [Everywhere]
        public static IEnumerable<CodeInstruction> Transpiler(
            IEnumerable<CodeInstruction> instructions,
            MethodBase patchedMethod
        )
        {
            return GameProjectionPcu.Transpile(instructions, patchedMethod);
        }
    }
}
