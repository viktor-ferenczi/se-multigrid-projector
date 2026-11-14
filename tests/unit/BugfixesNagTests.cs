using MultigridProjector.Utilities;
using Xunit;

// The missing Bugfixes plugin warning. Remove it with the warning, see BugfixesCheck.
public class BugfixesNagTests
{
    private const long Now = 1_800_000_000;
    private const long Week = 7 * 24 * 3600;

    [Theory]
    [InlineData(0, true)] // never shown
    [InlineData(Now, false)]
    [InlineData(Now - 3600, false)]
    [InlineData(Now - Week + 1, false)]
    [InlineData(Now - Week, true)]
    [InlineData(Now - 30 * 24 * 3600, true)]
    [InlineData(Now + 3600, true)] // the clock was set back
    [InlineData(-5, true)]
    public void TheDialogIsDueAWeekAfterItWasShown(long lastShown, bool due)
    {
        Assert.Equal(due, BugfixesNag.IsDue(lastShown, Now));
    }

    [Fact]
    public void NothingToSayWithTheFixInPlace()
    {
        Assert.Null(BugfixesNag.LogMessage(BugfixesState.Fixed));
        Assert.Null(BugfixesNag.DialogMessage(BugfixesState.Fixed));
    }

    [Theory]
    [InlineData(BugfixesState.Missing)]
    [InlineData(BugfixesState.TooOld)]
    public void TheWarningsNameThePluginAndItsVersion(BugfixesState state)
    {
        Assert.Contains("Bugfixes plugin", BugfixesNag.LogMessage(state));
        Assert.Contains("1.19.0", BugfixesNag.LogMessage(state));
        Assert.Contains("Bugfixes plugin", BugfixesNag.DialogMessage(state));
    }
}
