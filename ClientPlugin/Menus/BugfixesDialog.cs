using System;
using System.Text;
using ClientPlugin;
using ClientPlugin.Settings;
using MultigridProjector.Utilities;
using Sandbox.Game.Screens;
using Sandbox.Game.World;
using Sandbox.Graphics.GUI;
using VRageMath;

namespace MultigridProjectorClient.Menus
{
    // The client side of the missing Bugfixes plugin warning: the log line on every start, and
    // a dialog on the main menu the first time only. Remove it with the warning, see
    // BugfixesCheck.
    internal static class BugfixesDialog
    {
        private static bool detected;
        private static BugfixesState state;
        private static bool due;

        // Called on every update of the plugin, also on the main menu
        public static void Update()
        {
            if (!detected)
            {
                // The first update: every plugin is initialized by now, in whatever order
                // Pulsar took them
                detected = true;
                state = BugfixesCheck.DetectAndWarn();
                due = state != BugfixesState.Fixed && !Config.Current.BugfixesWarningShown;
            }

            if (!due)
                return;

            // Wait for the main menu to be the screen in front. With a world loading right at the
            // start there is none, then the dialog comes up once the player is back on it.
            if (MySession.Static != null || !(MyScreenManager.GetScreenWithFocus() is MyGuiScreenMainMenuBase))
                return;

            due = false;
            try
            {
                MyGuiSandbox.AddScreen(CreateDialog());

                // This deliberately ignores the Show Warning Dialogs option: the dialog comes
                // up only once and the leak ends in a crash
                Config.Current.BugfixesWarningShown = true;
                ConfigStorage.Save(Config.Current);
            }
            catch (Exception e)
            {
                PluginLog.Warn($"Could not show the missing Bugfixes plugin dialog: {e.Message}");
            }
        }

        private static MyGuiScreenMessageBox CreateDialog()
        {
            MyGuiScreenMessageBox messageBox = MyGuiSandbox.CreateMessageBox(
                MyMessageBoxStyleEnum.Info,
                messageText: new StringBuilder(BugfixesNag.DialogMessage(state)),
                messageCaption: new StringBuilder("Multigrid Projector - Bugfixes Plugin Recommended"),
                size: new Vector2(0.65f, 0.3f));

            // Make the background color less transparent, as the default is very faint and this is an important message
            messageBox.BackgroundColor = new Vector4(1f, 1f, 1f, 10.0f);

            return messageBox;
        }
    }
}
