using HarmonyLib;
using Sandbox.Game.Entities;

namespace MultigridProjector.Patches
{
    [HarmonyPatch(typeof(MyBlueprintIdTracker))]
    public static class MyBlueprintIdTrackerPatches
    {
        [HarmonyPrefix]
        [HarmonyPatch(nameof(MyBlueprintIdTracker.OnRemap))]
        private static bool OnRemapPrefix()
        {
            return false;
        }

        [HarmonyPrefix]
        [HarmonyPatch(nameof(MyBlueprintIdTracker.OnAdded))]
        private static bool OnAddedPrefix()
        {
            return false;
        }

        [HarmonyPrefix]
        [HarmonyPatch(nameof(MyBlueprintIdTracker.OnRemove))]
        private static bool OnRemovePrefix()
        {
            return false;
        }
    }
}