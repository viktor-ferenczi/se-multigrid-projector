using System;
using System.Linq;
using HarmonyLib;
using Sandbox.Game.Entities;

namespace MultigridProjector.Utilities
{
    // Warns when the Bugfixes plugin (CometWorks/bugfixes) does not run next to this plugin.
    //
    // The game's block placement test, MyCubeGrid.TestBlockPlacementArea, leaks Havok shapes
    // on every check of a projected armor block. The hand welder and the ship welders run that
    // test, and so does this plugin's Ship Welding. Ship Welding checks only every 10th frame
    // since 1.0.1, which slows the leak down but cannot stop it: the fix is a transpiler on the
    // game's method in Bugfixes 1.19.0 and newer (CometWorks/bugfixes#44). This plugin does not
    // patch that method.
    //
    // REMOVE THIS MECHANISM once the game itself stops leaking in the vanilla build and weld
    // process, when tests/ds/test_havok_leak_ds.py fails without Bugfixes because the memory
    // stays flat: this file, BugfixesNag.cs, ClientPlugin/Menus/BugfixesDialog.cs, the calls in
    // Update of both Plugin classes, Config.BugfixesWarningShownUnixTime, and their tests
    // (tests/unit/BugfixesNagTests.cs, tests/test_bugfixes_warning.py,
    // tests/ds/test_bugfixes_warning_ds.py).
    public static class BugfixesCheck
    {
        // Bugfixes patches with new Harmony(Plugin.Name) on the client and on the server
        private const string BugfixesHarmonyId = "Bugfixes";

        // Looks for the transpiler of Bugfixes on the game's method instead of the plugin itself.
        // That works the same under every loader, needs no reference to Bugfixes, and also finds
        // a Bugfixes too old to have the fix or one whose patch failed. Call it only once every
        // plugin is initialized, so from the first Update. Never throws.
        public static BugfixesState Detect()
        {
            try
            {
                // The overload with the most parameters, the one Bugfixes patches
                var method = AccessTools.GetDeclaredMethods(typeof(MyCubeGrid))
                    .Where(m => m.Name == nameof(MyCubeGrid.TestBlockPlacementArea))
                    .OrderByDescending(m => m.GetParameters().Length)
                    .FirstOrDefault();

                // The game has changed, so nothing is known about the leak anymore
                if (method == null)
                    return BugfixesState.Fixed;

                var patches = Harmony.GetPatchInfo(method);
                if (patches != null && patches.Transpilers.Any(p => p.owner == BugfixesHarmonyId))
                    return BugfixesState.Fixed;

                return Harmony.HasAnyPatches(BugfixesHarmonyId) ? BugfixesState.TooOld : BugfixesState.Missing;
            }
            catch (Exception e)
            {
                PluginLog.Info($"Could not check for the Bugfixes plugin: {e.Message}");
                return BugfixesState.Fixed;
            }
        }

        // Logs the warning if there is one to give. Never throws.
        public static BugfixesState DetectAndWarn()
        {
            var state = Detect();
            try
            {
                var message = BugfixesNag.LogMessage(state);
                if (message != null)
                    PluginLog.Warn(message);
            }
            catch (Exception)
            {
                // No logger: nothing to warn with
            }

            return state;
        }
    }
}
