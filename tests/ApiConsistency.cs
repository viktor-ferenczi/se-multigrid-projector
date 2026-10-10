// Programmable block script of the MGP tests (GitHub issue #114): checks on
// every tick that what MGP's PB API says about one projection holds together,
// the way a script that reads the API every tick relies on it. The test world
// fills in the projector id. It echoes, one line per fact:
//
//   run <ticks checked>
//   scan <scan number>
//   fail <kind> <count> <first example>
//
// The kinds of failure:
//   state      GetBlockState disagrees with GetBlockStates in the same tick
//   position   GetBlockStates names a cell the preview grid has no block in
//   complete   IsSubgridComplete is true while a block is not fully built
//   connection a base connection points at a subgrid that doesn't exist
//   hash       a subgrid's state hash changed while the scan number stayed the
//              same; the API says it changes only with a new scan
//   unscanned  a block state changed while the scan number stayed the same

static readonly long Projector = /*PROJECTOR*/;
const int FullyBuilt = 8;

Delegate[] api;
long ticks;
long lastScan = -1;
List<Dictionary<Vector3I, int>> lastStates = new List<Dictionary<Vector3I, int>>();
List<ulong> lastHashes = new List<ulong>();
readonly Dictionary<string, long> fails = new Dictionary<string, long>();
readonly Dictionary<string, string> examples = new Dictionary<string, string>();

public Program()
{
    Runtime.UpdateFrequency = UpdateFrequency.Update1;
}

void Fail(string kind, string example)
{
    long count;
    fails.TryGetValue(kind, out count);
    fails[kind] = count + 1;
    if (!examples.ContainsKey(kind))
        examples[kind] = example;
}

public void Main(string argument, UpdateType updateSource)
{
    api = api ?? Me.GetProperty("MgpApi")?.As<Delegate[]>().GetValue(Me);
    if (api == null)
    {
        Echo("no api");
        return;
    }

    var scan = ((Func<long, long>)api[8])(Projector);
    var count = ((Func<long, int>)api[1])(Projector);
    var states = new List<Dictionary<Vector3I, int>>();
    var hashes = new List<ulong>();
    var box = new BoundingBoxI(Vector3I.MinValue, Vector3I.MaxValue);
    for (var i = 0; i < count; i++)
    {
        var map = new Dictionary<Vector3I, int>();
        ((Func<Dictionary<Vector3I, int>, long, int, BoundingBoxI, int, bool>)api[5])(map, Projector, i, box, ~0);
        var preview = ((Func<long, int, IMyCubeGrid>)api[2])(Projector, i);
        var allBuilt = true;
        foreach (var pair in map)
        {
            var state = ((Func<long, int, Vector3I, int>)api[4])(Projector, i, pair.Key);
            if (state != pair.Value)
                Fail("state", $"{i}:{pair.Key}:{pair.Value}->{state}");
            if (preview == null || !preview.CubeExists(pair.Key))
                Fail("position", $"{i}:{pair.Key}");
            if (pair.Value != FullyBuilt)
                allBuilt = false;
        }
        if (((Func<long, int, bool>)api[11])(Projector, i) && !allBuilt)
            Fail("complete", $"{i}");

        var bases = new List<Vector3I>();
        var tops = new List<int>();
        var topPositions = new List<Vector3I>();
        if (((Func<long, int, List<Vector3I>, List<int>, List<Vector3I>, bool>)api[6])(Projector, i, bases, tops, topPositions))
        {
            foreach (var top in tops)
                if (top < 0 || top >= count)
                    Fail("connection", $"{i}->{top}");
        }

        states.Add(map);
        hashes.Add(((Func<long, int, ulong>)api[10])(Projector, i));
    }

    // Compare with the last tick only if no scan finished in between, nor
    // during this tick
    var scanAfter = ((Func<long, long>)api[8])(Projector);
    if (scan == lastScan && scanAfter == scan && states.Count == lastStates.Count)
    {
        for (var i = 0; i < states.Count; i++)
        {
            if (hashes[i] != lastHashes[i])
                Fail("hash", $"{i}");
            foreach (var pair in states[i])
            {
                int last;
                if (!lastStates[i].TryGetValue(pair.Key, out last) || last != pair.Value)
                {
                    Fail("unscanned", $"{i}:{pair.Key}:{last}->{pair.Value}");
                    break;
                }
            }
        }
    }
    lastScan = scanAfter == scan ? scan : -1;
    lastStates = states;
    lastHashes = hashes;
    ticks++;

    var sb = new StringBuilder();
    sb.Append("run ").Append(ticks).Append('\n');
    sb.Append("scan ").Append(scanAfter).Append('\n');
    foreach (var pair in fails)
        sb.Append("fail ").Append(pair.Key).Append(' ').Append(pair.Value).Append(' ').Append(examples[pair.Key]).Append('\n');
    Echo(sb.ToString());
}
