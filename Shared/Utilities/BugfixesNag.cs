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

    // The texts of the missing Bugfixes plugin warning, see BugfixesCheck.
    // Remove it together with BugfixesCheck.
    public static class BugfixesNag
    {
        // The first Bugfixes version with the fix (CometWorks/bugfixes#44)
        public const string MinVersion = "1.19.0";

        // Null if there is nothing to warn about
        public static string LogMessage(BugfixesState state)
        {
            switch (state)
            {
                case BugfixesState.Missing:
                    return "The Bugfixes plugin is not loaded. It fixes a memory leak in the welders' block checks, so using it together with Multigrid Projector is recommended.";
                case BugfixesState.TooOld:
                    return $"The Bugfixes plugin is loaded without its fix of a memory leak in the welders' block checks. Update it to {MinVersion} or newer.";
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
                    return "The Bugfixes plugin fixes a memory leak in the welders' block checks.\n" +
                           "Using it together with Multigrid Projector is recommended.";
                case BugfixesState.TooOld:
                    return "The Bugfixes plugin fixes a memory leak in the welders' block checks,\n" +
                           $"but only from version {MinVersion}. Please update it.";
                default:
                    return null;
            }
        }
    }
}
