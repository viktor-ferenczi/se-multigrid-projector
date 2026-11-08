using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

// ReSharper disable once CheckNamespace
namespace MultigridProjector.Utilities
{
    // The wire format of MGP's mod channel and the server's presence schedule. Kept free of game
    // types, so the unit tests in tests/unit can compile it without the game.
    //
    // A server with the MGP plugin sends each client a presence packet: the plugin version as
    // ASCII, like "1.0.0". A client switches to its full feature set only on a presence packet of
    // its own major version. Until then it sends exactly what a vanilla client sends.
    //
    // In full mode the client asks the server for each projected block it welds with a build
    // request on the same channel: a type byte, then the fields of BuildRequest, little endian.
    public static class Presence
    {
        // Fixed by SE-1273. Nothing else known (plugins, mods, scripts, worlds) uses it.
        public const ushort Channel = 0xD83A;

        // MGP 0.9.x clients switch to full mode on any server packet on this channel
        public const ushort LegacyChannel = 0x7b94;

        public const byte BuildRequestType = 1;

        private const int MaxVersionLength = 32;

        public static byte[] EncodePresence(string version) => Encoding.ASCII.GetBytes(version);

        // A version is 2 to 4 dot separated non-negative integers, like "1.0.0"
        public static bool TryParseVersion(byte[] data, out string version, out int major)
        {
            version = null;
            major = -1;

            if (data == null || data.Length == 0 || data.Length > MaxVersionLength)
                return false;

            foreach (var b in data)
                if (b != '.' && (b < '0' || b > '9'))
                    return false;

            var text = Encoding.ASCII.GetString(data);
            var parts = text.Split('.');
            if (parts.Length < 2 || parts.Length > 4)
                return false;

            foreach (var part in parts)
                if (part.Length == 0 || part.Length > 9)
                    return false;

            version = text;
            major = int.Parse(parts[0]);
            return true;
        }

        public static int Major(string version) => int.Parse(version.Split('.')[0]);

        // A client takes the full feature set only from a server of its own major version
        public static bool IsCompatible(
            byte[] presence,
            string clientVersion,
            out string serverVersion
        )
        {
            return TryParseVersion(presence, out serverVersion, out var major)
                && major == Major(clientVersion);
        }
    }

    public struct BuildRequest
    {
        public long ProjectorId;
        public int SubgridIndex;
        public int X,
            Y,
            Z;
        public long Owner;
        public long Builder;
        public bool RequestInstant;

        private const int Length = 1 + 8 + 4 + 3 * 4 + 8 + 8 + 1;

        public byte[] Encode()
        {
            using (var stream = new MemoryStream(Length))
            using (var writer = new BinaryWriter(stream))
            {
                writer.Write(Presence.BuildRequestType);
                writer.Write(ProjectorId);
                writer.Write(SubgridIndex);
                writer.Write(X);
                writer.Write(Y);
                writer.Write(Z);
                writer.Write(Owner);
                writer.Write(Builder);
                writer.Write(RequestInstant);
                writer.Flush();
                return stream.ToArray();
            }
        }

        public static bool TryDecode(byte[] data, out BuildRequest request)
        {
            request = default;
            if (data == null || data.Length != Length || data[0] != Presence.BuildRequestType)
                return false;

            using (var reader = new BinaryReader(new MemoryStream(data, 1, Length - 1)))
            {
                request.ProjectorId = reader.ReadInt64();
                request.SubgridIndex = reader.ReadInt32();
                request.X = reader.ReadInt32();
                request.Y = reader.ReadInt32();
                request.Z = reader.ReadInt32();
                request.Owner = reader.ReadInt64();
                request.Builder = reader.ReadInt64();
                request.RequestInstant = reader.ReadBoolean();
            }

            return request.SubgridIndex >= 0;
        }
    }

    // When to send the presence packet to whom: a delay after a client shows up among the online
    // players, then once every interval. The repeat covers lost packets and players arriving
    // without a connect event, like on a cluster node switch. Times are seconds of any clock.
    public class PresenceSchedule
    {
        private readonly Dictionary<ulong, double> nextSend = new Dictionary<ulong, double>();
        private readonly List<ulong> due = new List<ulong>();
        private readonly HashSet<ulong> seen = new HashSet<ulong>();
        private readonly List<ulong> gone = new List<ulong>();

        public List<ulong> Due(IEnumerable<ulong> online, double now, double delay, double interval)
        {
            due.Clear();
            seen.Clear();

            foreach (var steamId in online)
            {
                seen.Add(steamId);

                if (!nextSend.TryGetValue(steamId, out var at))
                {
                    nextSend[steamId] = now + delay;
                    at = nextSend[steamId];
                }

                if (now < at)
                    continue;

                due.Add(steamId);
                nextSend[steamId] = now + Math.Max(1.0, interval);
            }

            // A client that left waits out the delay again when it comes back
            gone.Clear();
            foreach (var steamId in nextSend.Keys)
                if (!seen.Contains(steamId))
                    gone.Add(steamId);
            foreach (var steamId in gone)
                nextSend.Remove(steamId);

            return due;
        }
    }

    // Build requests a sender may make per second, outside creative
    public class BuildRateLimit
    {
        private readonly Dictionary<ulong, (double start, int count)> windows =
            new Dictionary<ulong, (double, int)>();

        public bool Allow(ulong sender, double now, int perSecond)
        {
            if (!windows.TryGetValue(sender, out var window) || now - window.start >= 1.0)
            {
                windows[sender] = (now, 1);
                return true;
            }

            windows[sender] = (window.start, window.count + 1);
            return window.count < perSecond;
        }
    }
}
