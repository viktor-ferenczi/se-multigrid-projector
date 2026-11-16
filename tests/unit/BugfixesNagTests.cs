using MultigridProjector.Utilities;
using Xunit;

// The missing Bugfixes plugin warning. Remove it with the warning, see BugfixesCheck.
public class BugfixesNagTests
{
    [Fact]
    public void NothingToSayWithTheFixInPlace()
    {
        Assert.Null(BugfixesNag.LogMessage(BugfixesState.Fixed));
        Assert.Null(BugfixesNag.DialogMessage(BugfixesState.Fixed));
    }

    [Fact]
    public void WithoutBugfixesTheWarningsRecommendIt()
    {
        Assert.Contains("The Bugfixes plugin is not loaded", BugfixesNag.LogMessage(BugfixesState.Missing));
        Assert.Contains("is recommended", BugfixesNag.LogMessage(BugfixesState.Missing));
        Assert.Contains("is recommended", BugfixesNag.DialogMessage(BugfixesState.Missing));
    }

    [Fact]
    public void WithAnOldBugfixesTheWarningsNameTheVersionToUpdateTo()
    {
        Assert.Contains("1.19.0", BugfixesNag.LogMessage(BugfixesState.TooOld));
        Assert.Contains("1.19.0", BugfixesNag.DialogMessage(BugfixesState.TooOld));
    }
}
