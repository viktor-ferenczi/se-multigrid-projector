using System;

namespace MultigridProjector.Utilities
{
    public enum BugfixesState
    {
        // The Bugfixes plugin has patched the game's block placement test, or it cannot be told
        Fixed,

        // The Bugfixes plugin is loaded, but its patch of the block placement test is not applied
        TooOld,

        // No Bugfixes plugin
        Missing,
    }

    // The texts and the timing of the missing Bugfixes plugin warning, see BugfixesCheck.
    // Remove it together with BugfixesCheck.
    public static class BugfixesNag
    {
        // The first Bugfixes version with the fix (CometWorks/bugfixes#44)
        public const string MinVersion = "1.19.0";

        public const long IntervalSeconds = 7 * 24 * 3600;

        private const string Why =
            "The game leaks Havok memory when welders check projected blocks, " +
            "until the game runs out of memory. Only the Bugfixes plugin fixes that.";

        // The dialog is due a week after it was last shown. A time in the future is a clock set
        // back since then, and counts as never shown.
        public static bool IsDue(long lastShownUnixTime, long nowUnixTime)
        {
            return lastShownUnixTime <= 0
                   || lastShownUnixTime > nowUnixTime
                   || nowUnixTime - lastShownUnixTime >= IntervalSeconds;
        }

        // Null if there is nothing to warn about
        public static string LogMessage(BugfixesState state)
        {
            switch (state)
            {
                case BugfixesState.Missing:
                    return $"The Bugfixes plugin is not loaded. {Why} Use the Bugfixes plugin ({MinVersion} or newer) together with Multigrid Projector.";
                case BugfixesState.TooOld:
                    return $"The Bugfixes plugin is loaded without its fix of the block placement test. {Why} Update the Bugfixes plugin to {MinVersion} or newer and check its log lines for a failed patch.";
                default:
                    return null;
            }
        }

        // Null if there is nothing to warn about
        public static string DialogMessage(BugfixesState state)
        {
            switch (state)
            {
                case BugfixesState.Missing:
                    return "The Bugfixes plugin is not enabled.\n\n" +
                           "The game leaks memory when welders check projected blocks,\n" +
                           "until it runs out of memory and crashes.\n" +
                           "Only the Bugfixes plugin fixes that.\n\n" +
                           "Please enable the Bugfixes plugin in the Plugins menu\n" +
                           "and restart the game.";
                case BugfixesState.TooOld:
                    return "The Bugfixes plugin is enabled, but its fix of the memory leak\n" +
                           "is not active.\n\n" +
                           "The game leaks memory when welders check projected blocks,\n" +
                           "until it runs out of memory and crashes.\n\n" +
                           $"Please update the Bugfixes plugin to {MinVersion} or newer\n" +
                           "and restart the game.";
                default:
                    return null;
            }
        }
    }
}
