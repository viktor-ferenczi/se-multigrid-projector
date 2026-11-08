using System.Linq;
using System.Text;
using MultigridProjector.Utilities;
using Xunit;

public class PresenceTests
{
    private static byte[] Bytes(string text) => Encoding.ASCII.GetBytes(text);

    [Theory]
    [InlineData("1.0.0", 1)]
    [InlineData("1.2", 1)]
    [InlineData("2.10.3.4", 2)]
    [InlineData("0.9.12", 0)]
    public void ParsesVersions(string text, int major)
    {
        Assert.True(Presence.TryParseVersion(Bytes(text), out var version, out var parsedMajor));
        Assert.Equal(text, version);
        Assert.Equal(major, parsedMajor);
    }

    [Theory]
    [InlineData("")]
    [InlineData("1")]
    [InlineData("1.0.0.0.0")]
    [InlineData("1..0")]
    [InlineData(".1.0")]
    [InlineData("v1.0.0")]
    [InlineData("1.0.0-beta")]
    [InlineData("1.0.0 ")]
    [InlineData("1234567890.0")]
    public void RefusesWhatIsNotAVersion(string text)
    {
        Assert.False(Presence.TryParseVersion(Bytes(text), out _, out _));
    }

    [Fact]
    public void RefusesTheLegacySignatureAndProtobufWrappedBytes()
    {
        // What a 0.9.x server sends on the old channel, raw and as SendToClient serialized it
        Assert.False(
            Presence.TryParseVersion(new byte[] { 2, 3, 5, 7, 11, 13, 17, 19 }, out _, out _)
        );
        Assert.False(
            Presence.TryParseVersion(new byte[] { 10, 8, 2, 3, 5, 7, 11, 13, 17, 19 }, out _, out _)
        );
        Assert.False(Presence.TryParseVersion(null, out _, out _));
        Assert.False(
            Presence.TryParseVersion(Enumerable.Repeat((byte)'1', 64).ToArray(), out _, out _)
        );
    }

    [Theory]
    [InlineData("1.0.0", "1.0.0", true)]
    [InlineData("1.4.2", "1.0.0", true)]
    [InlineData("1.0.0", "1.9", true)]
    [InlineData("2.0.0", "1.0.0", false)]
    [InlineData("0.9.12", "1.0.0", false)]
    [InlineData("10.0.0", "1.0.0", false)]
    [InlineData("1.0.0-rc", "1.0.0", false)]
    public void CompatibleOnlyWithTheSameMajor(string server, string client, bool compatible)
    {
        Assert.Equal(compatible, Presence.IsCompatible(Bytes(server), client, out _));
    }

    [Fact]
    public void EncodesThePlainVersion()
    {
        Assert.Equal(Bytes("1.0.0"), Presence.EncodePresence("1.0.0"));
        Assert.Equal(1, Presence.Major("1.0.0"));
    }

    [Fact]
    public void BuildRequestRoundTrips()
    {
        var request = new BuildRequest
        {
            ProjectorId = 0x1234_5678_9ABC_DEF0,
            SubgridIndex = 3,
            X = -7,
            Y = 0,
            Z = 12,
            Owner = 144115188075855873,
            Builder = 99,
            RequestInstant = true,
        };

        var data = request.Encode();
        Assert.Equal(Presence.BuildRequestType, data[0]);
        Assert.True(BuildRequest.TryDecode(data, out var decoded));
        Assert.Equal(request, decoded);
    }

    [Fact]
    public void BuildRequestRefusesOtherPackets()
    {
        var data = new BuildRequest { SubgridIndex = 1 }.Encode();
        Assert.False(BuildRequest.TryDecode(data.Take(data.Length - 1).ToArray(), out _));
        Assert.False(BuildRequest.TryDecode(Bytes("1.0.0"), out _));
        Assert.False(
            BuildRequest.TryDecode(new BuildRequest { SubgridIndex = -1 }.Encode(), out _)
        );

        data[0] = 2;
        Assert.False(BuildRequest.TryDecode(data, out _));
    }

    [Fact]
    public void ScheduleSendsAfterTheDelayThenAtTheInterval()
    {
        var schedule = new PresenceSchedule();
        ulong[] online = { 7 };

        Assert.Empty(schedule.Due(online, 100, 5, 300));
        Assert.Empty(schedule.Due(online, 104, 5, 300));
        Assert.Equal(online, schedule.Due(online, 105, 5, 300));
        Assert.Empty(schedule.Due(online, 106, 5, 300));
        Assert.Empty(schedule.Due(online, 404, 5, 300));
        Assert.Equal(online, schedule.Due(online, 405, 5, 300));
    }

    [Fact]
    public void ScheduleStartsOverForAClientThatCameBack()
    {
        var schedule = new PresenceSchedule();

        schedule.Due(new ulong[] { 7, 8 }, 0, 2, 300);
        Assert.Equal(new ulong[] { 7, 8 }, schedule.Due(new ulong[] { 7, 8 }, 2, 2, 300));

        // 8 leaves (a node switch on a cluster looks the same), then comes back
        schedule.Due(new ulong[] { 7 }, 3, 2, 300);
        Assert.Empty(schedule.Due(new ulong[] { 7, 8 }, 4, 2, 300));
        Assert.Equal(new ulong[] { 8 }, schedule.Due(new ulong[] { 7, 8 }, 6, 2, 300));
    }

    [Fact]
    public void ScheduleWithoutDelaySendsAtOnce()
    {
        var schedule = new PresenceSchedule();
        Assert.Equal(new ulong[] { 7 }, schedule.Due(new ulong[] { 7 }, 0, 0, 1));
        Assert.Empty(schedule.Due(new ulong[] { 7 }, 0.5, 0, 1));
        Assert.Equal(new ulong[] { 7 }, schedule.Due(new ulong[] { 7 }, 1, 0, 1));
    }

    [Fact]
    public void RateLimitAllowsPerSecondPerSender()
    {
        var limit = new BuildRateLimit();
        Assert.True(limit.Allow(1, 0.0, 2));
        Assert.True(limit.Allow(1, 0.1, 2));
        Assert.False(limit.Allow(1, 0.2, 2));
        Assert.True(limit.Allow(2, 0.2, 2));
        Assert.True(limit.Allow(1, 1.0, 2));
    }
}
