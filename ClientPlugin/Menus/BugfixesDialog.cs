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
    // The client side of the missing Bugfixes plugin warning: the log line, and a dialog on the
    // main menu at most once a week. Remove it with the warning, see BugfixesCheck.
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
                due = state != BugfixesState.Fixed && BugfixesNag.IsDue(Config.Current.BugfixesWarningShownUnixTime, Now);
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

                // This deliberately ignores the Show Warning Dialogs option: the dialog is rare
                // and the leak ends in a crash
                Config.Current.BugfixesWarningShownUnixTime = Now;
                ConfigStorage.Save(Config.Current);
            }
            catch (Exception e)
            {
                PluginLog.Warn($"Could not show the missing Bugfixes plugin dialog: {e.Message}");
            }
        }

        private static long Now => DateTimeOffset.UtcNow.ToUnixTimeSeconds();

        private static MyGuiScreenMessageBox CreateDialog()
        {
            MyGuiScreenMessageBox messageBox = MyGuiSandbox.CreateMessageBox(
                MyMessageBoxStyleEnum.Info,
                messageText: new StringBuilder(BugfixesNag.DialogMessage(state)),
                messageCaption: new StringBuilder("Multigrid Projector - Bugfixes Plugin Needed"),
                size: new Vector2(0.65f, 0.4f));

            // Make the background color less transparent, as the default is very faint and this is an important message
            messageBox.BackgroundColor = new Vector4(1f, 1f, 1f, 10.0f);

            return messageBox;
        }
    }
}
