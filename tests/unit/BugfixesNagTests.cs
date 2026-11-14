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
