using System;
using System.Linq;
using Sandbox.Game.Entities;
using Sandbox.Game.Entities.Blocks;
using SpaceEngineers.Game.Entities.Blocks;
using VRage.Plugins;
using VRage.Utils;

namespace ToolProbe
{
    // Test only, for test_build_checks_ds.py: builds a projected block on the server the way
    // ToolCore's welders do, with projector.Build, the server as the sender and a block (here the
    // projector itself) as the builder, which holds no components. The test asks for it with a
    // "serverBuild=<subtype>" line in the projector's custom data.
    // ReSharper disable once UnusedType.Global
    public class Plugin : IPlugin
    {
        private const string Key = "serverBuild=";
        private int tick;

        public void Init(object gameInstance) { }

        public void Update()
        {
            if (++tick % 30 != 0)
                return;

            foreach (var grid in MyEntities.GetEntities().OfType<MyCubeGrid>().ToList())
            foreach (var projector in grid.GetFatBlocks<MySpaceProjector>())
            {
                var line = projector
                    .CustomData.Split('\n')
                    .Select(l => l.Trim())
                    .FirstOrDefault(l => l.StartsWith(Key));
                if (line != null)
                    Build(projector, line.Substring(Key.Length));
            }
        }

        private static void Build(MySpaceProjector projector, string subtype)
        {
            projector.CustomData = "";
            try
            {
                var block = projector.ProjectedGrid?.CubeBlocks.FirstOrDefault(b =>
                    b.BlockDefinition.Id.SubtypeName == subtype
                    && projector.CanBuild(b, true) == BuildCheckResult.OK
                );
                if (block == null)
                {
                    MyLog.Default.WriteLineAndConsole($"ToolProbe: no buildable {subtype}");
                    return;
                }

                projector.Build(
                    block,
                    projector.OwnerId,
                    projector.EntityId,
                    false,
                    projector.OwnerId
                );
                MyLog.Default.WriteLineAndConsole(
                    $"ToolProbe: asked for {subtype} at {block.Position}"
                );
            }
            catch (Exception e)
            {
                MyLog.Default.WriteLineAndConsole($"ToolProbe: failed: {e}");
            }
        }

        public void Dispose() { }
    }
}
