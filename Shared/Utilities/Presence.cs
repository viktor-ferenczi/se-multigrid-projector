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
    // A server with the MGP plugin sends each client a presence packet: the protocol id and the
    // plugin version as ASCII, separated by a space, like
    // "ada94b93-b115-4fa6-9cd9-8e4766d87706 1.0.0". A client switches to its full feature set only
    // on a presence packet with its own protocol id. Until then it sends exactly what a vanilla
    // client sends. The version is only for the logs.
    //
    // In full mode the client asks the server for each projected block it welds with a build
    // request on the same channel: a type byte, then the fields of BuildRequest, little endian.
    public static class Presence
    {
        // Fixed by SE-1273. Nothing else known (plugins, mods, scripts, worlds) uses it.
        public const ushort Channel = 0xD83A;

        // MGP 0.9.x clients switch to full mode on any server packet on this channel
        public const ushort LegacyChannel = 0x7b94;

        // Replace it with a new random UUID (uuid4) in any update that would break the client and
        // server plugins talking to each other: a change of the mod messages, or of state the two
        // sides can't reconcile. Clients and servers with different ids then work as with a vanilla
        // counterpart. Not the plugin's Id, and unrelated to the version and to the MGP API.
        public static readonly Guid ProtocolId = new Guid("ada94b93-b115-4fa6-9cd9-8e4766d87706");

        public const byte BuildRequestType = 1;

        private const int MaxLength = 64;

        public static byte[] EncodePresence(Guid protocolId, string version) =>
            Encoding.ASCII.GetBytes($"{protocolId:D} {version}");

        // A presence packet: a protocol id in the "D" format, a space and a version of 2 to 4 dot
        // separated non-negative integers
        public static bool TryParsePresence(byte[] data, out Guid protocolId, out string version)
        {
            protocolId = Guid.Empty;
            version = null;

            if (data == null || data.Length == 0 || data.Length > MaxLength)
                return false;

            foreach (var b in data)
                if (b < 0x20 || b > 0x7e)
                    return false;

            var parts = Encoding.ASCII.GetString(data).Split(' ');
            if (
                parts.Length != 2
                || !Guid.TryParseExact(parts[0], "D", out var id)
                || !IsVersion(parts[1])
            )
                return false;

            protocolId = id;
            version = parts[1];
            return true;
        }

        private static bool IsVersion(string text)
        {
            var parts = text.Split('.');
            if (parts.Length < 2 || parts.Length > 4)
                return false;

            foreach (var part in parts)
            {
                if (part.Length == 0 || part.Length > 9)
                    return false;

                foreach (var c in part)
                    if (c < '0' || c > '9')
                        return false;
            }

            return true;
        }

        // A client takes the full feature set only from a server with its own protocol id
        public static bool IsCompatible(
            byte[] presence,
            Guid protocolId,
            out string serverVersion
        ) =>
            TryParsePresence(presence, out var serverProtocolId, out serverVersion)
            && serverProtocolId == protocolId;
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
