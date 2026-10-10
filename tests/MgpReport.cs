// Programmable block script of the MGP tests: echoes what the plugin's PB API
// says about the test projections, every 100 ticks. It runs by itself, so it
// works the same in single player and on a server, where a client cannot ask it
// to run. The echo reaches a client as the block's detailed info, which the
// server sends to the clients that subscribe to it; custom data the script
// writes on a server is not sent to clients. The test world fills in the projector
// ids. One line per fact:
//
//   run <number of this report>
//   projector <entity id>
//   version <MGP version>
//   scan <scan number>
//   subgrids <count>
//   subgrid <index> <preview grid id> <built grid id or 0> <complete 0|1>
//   count <subgrid> <state> <number of blocks>
//   open <subgrid> <state> <x>,<y>,<z> ...      (every state but FullyBuilt)
//   base <subgrid> <x>,<y>,<z> <top subgrid> <x>,<y>,<z>
//
// States are MGP's BlockState values, positions are preview grid cells. The
// echo is cut at 8000 characters, hence the counts and the short lines.

static readonly long[] Projectors = { /*PROJECTORS*/ };

Delegate[] api;
long run;

public Program()
{
    Runtime.UpdateFrequency = UpdateFrequency.Update100;
}

public void Main(string argument, UpdateType updateSource)
{
    // Looked up on each run: the script may compile before the plugin
    // registered the property
    api = api ?? Me.GetProperty("MgpApi")?.As<Delegate[]>().GetValue(Me);
    var sb = new StringBuilder();
    sb.Append("run ").Append(++run).Append('\n');
    if (api == null)
    {
        Echo(sb.Append("no api\n").ToString());
        return;
    }

    foreach (var id in Projectors)
        Report(sb, id);
    Echo(sb.ToString());
}

void Report(StringBuilder sb, long id)
{
    sb.Append("projector ").Append(id).Append('\n');
    sb.Append("version ").Append(((Func<string>)api[0])()).Append('\n');
    sb.Append("scan ").Append(((Func<long, long>)api[8])(id)).Append('\n');
    var count = ((Func<long, int>)api[1])(id);
    sb.Append("subgrids ").Append(count).Append('\n');
    for (var i = 0; i < count; i++)
    {
        var preview = ((Func<long, int, IMyCubeGrid>)api[2])(id, i);
        var built = ((Func<long, int, IMyCubeGrid>)api[3])(id, i);
        var complete = ((Func<long, int, bool>)api[11])(id, i);
        sb.Append("subgrid ").Append(i).Append(' ')
            .Append(preview?.EntityId ?? 0).Append(' ')
            .Append(built?.EntityId ?? 0).Append(' ')
            .Append(complete ? 1 : 0).Append('\n');

        var states = new Dictionary<Vector3I, int>();
        var box = new BoundingBoxI(Vector3I.MinValue, Vector3I.MaxValue);
        ((Func<Dictionary<Vector3I, int>, long, int, BoundingBoxI, int, bool>)api[5])(states, id, i, box, ~0);
        var byState = new Dictionary<int, List<Vector3I>>();
        foreach (var pair in states)
        {
            List<Vector3I> cells;
            if (!byState.TryGetValue(pair.Value, out cells))
                byState[pair.Value] = cells = new List<Vector3I>();
            cells.Add(pair.Key);
        }
        foreach (var pair in byState)
        {
            sb.Append("count ").Append(i).Append(' ').Append(pair.Key).Append(' ').Append(pair.Value.Count).Append('\n');
            if (pair.Key == 8)
                continue;
            sb.Append("open ").Append(i).Append(' ').Append(pair.Key);
            foreach (var p in pair.Value)
                sb.Append(' ').Append(p.X).Append(',').Append(p.Y).Append(',').Append(p.Z);
            sb.Append('\n');
        }

        var basePositions = new List<Vector3I>();
        var topIndices = new List<int>();
        var topPositions = new List<Vector3I>();
        if (((Func<long, int, List<Vector3I>, List<int>, List<Vector3I>, bool>)api[6])(id, i, basePositions, topIndices, topPositions))
        {
            for (var j = 0; j < basePositions.Count; j++)
                sb.Append("base ").Append(i).Append(' ')
                    .Append(basePositions[j].X).Append(',').Append(basePositions[j].Y).Append(',').Append(basePositions[j].Z).Append(' ')
                    .Append(topIndices[j]).Append(' ')
                    .Append(topPositions[j].X).Append(',').Append(topPositions[j].Y).Append(',').Append(topPositions[j].Z).Append('\n');
        }
    }
}
