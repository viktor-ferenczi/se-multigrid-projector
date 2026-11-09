using System;
using System.Linq;
using System.Text;
using MultigridProjector.Utilities;
using Xunit;

public class PresenceTests
{
    private static byte[] Bytes(string text) => Encoding.ASCII.GetBytes(text);

    private const string Id = "ada94b93-b115-4fa6-9cd9-8e4766d87706";
    private static readonly Guid Other = new Guid("0f8e2c4d-6b1a-4e3f-9d2c-7a5b3e1f0c9d");

    [Fact]
    public void TheProtocolIdIsFixedInTheCode()
    {
        Assert.Equal(new Guid(Id), Presence.ProtocolId);
    }

    [Theory]
    [InlineData(Id + " 1.0.0", "1.0.0")]
    [InlineData(Id + " 1.2", "1.2")]
    [InlineData(Id + " 2.10.3.4", "2.10.3.4")]
    public void ParsesPresencePackets(string text, string version)
    {
        Assert.True(Presence.TryParsePresence(Bytes(text), out var protocolId, out var parsed));
        Assert.Equal(new Guid(Id), protocolId);
        Assert.Equal(version, parsed);
    }

    [Theory]
    [InlineData("")]
    [InlineData("1.0.0")]
    [InlineData(Id)]
    [InlineData(Id + " ")]
    [InlineData(Id + " 1")]
    [InlineData(Id + " 1.0.0.0.0")]
    [InlineData(Id + " 1..0")]
    [InlineData(Id + " v1.0.0")]
    [InlineData(Id + " 1.0.0-beta")]
    [InlineData(Id + " 1.0.0 ")]
    [InlineData(Id + "  1.0.0")]
    [InlineData(Id + " 1234567890.0")]
    [InlineData("1.0.0 " + Id)]
    [InlineData("{" + Id + "} 1.0.0")]
    [InlineData("ada94b93b1154fa69cd98e4766d87706 1.0.0")]
    [InlineData("not-a-guid-at-all-not-a-guid-at-all0 1.0.0")]
    public void RefusesWhatIsNotAPresencePacket(string text)
    {
        Assert.False(Presence.TryParsePresence(Bytes(text), out _, out _));
    }

    [Fact]
    public void RefusesTheLegacySignatureAndOtherBytes()
    {
        // What a 0.9.x server sends on the old channel, raw and as SendToClient serialized it
        Assert.False(
            Presence.TryParsePresence(new byte[] { 2, 3, 5, 7, 11, 13, 17, 19 }, out _, out _)
        );
        Assert.False(
            Presence.TryParsePresence(
                new byte[] { 10, 8, 2, 3, 5, 7, 11, 13, 17, 19 },
                out _,
                out _
            )
        );
        Assert.False(Presence.TryParsePresence(null, out _, out _));
        Assert.False(Presence.TryParsePresence(Bytes(Id + " 1.0.0\n"), out _, out _));
        Assert.False(
            Presence.TryParsePresence(Bytes(Id + " 1." + new string('0', 64)), out _, out _)
        );
    }

    [Fact]
    public void EncodesTheIdAndVersion()
    {
        Assert.Equal(Bytes(Id + " 1.0.0"), Presence.EncodePresence(new Guid(Id), "1.0.0"));
    }

    [Fact]
    public void CompatibleOnlyWithTheSameProtocolId()
    {
        var own = Presence.EncodePresence(Presence.ProtocolId, "7.3.1");
        Assert.True(Presence.IsCompatible(own, Presence.ProtocolId, out var version));
        Assert.Equal("7.3.1", version);

        // Same version, another protocol: not compatible
        var other = Presence.EncodePresence(Other, "1.0.0");
        Assert.False(Presence.IsCompatible(other, Presence.ProtocolId, out _));

        Assert.False(Presence.IsCompatible(Bytes("1.0.0"), Presence.ProtocolId, out _));
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
