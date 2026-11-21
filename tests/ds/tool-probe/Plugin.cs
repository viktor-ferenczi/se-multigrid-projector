using System;
using System.IO;
using System.Linq;
using Entities.Blocks;
using Sandbox.Game.Entities;
using Sandbox.ModAPI;
using VRage.FileSystem;
using VRage.Plugins;
using VRage.Utils;

namespace ToolProbe
{
    // Test only, for test_build_checks_ds.py: builds a projected block on the server the way
    // ToolCore's welders do, with projector.Build, the server as the sender and a block (here the
    // projector itself) as the builder, which holds no components. The test asks for it by
    // writing the block's subtype into ToolProbe.txt in the server's data folder: a projector's
    // custom data set by the test's client doesn't reach the server.
    // ReSharper disable once UnusedType.Global
    public class Plugin : IPlugin
    {
        private int tick;

        public void Init(object gameInstance) { }

        public void Update()
        {
            if (++tick % 30 != 0)
                return;

            var request = Path.Combine(MyFileSystem.UserDataPath, "ToolProbe.txt");
            if (!File.Exists(request))
                return;

            var subtype = File.ReadAllText(request).Trim();
            File.Delete(request);
            try
            {
                Build(subtype);
            }
            catch (Exception e)
            {
                MyLog.Default.WriteLineAndConsole($"ToolProbe: failed: {e}");
            }
        }

        private static void Build(string subtype)
        {
            foreach (var grid in MyEntities.GetEntities().OfType<MyCubeGrid>().ToList())
            foreach (var projector in grid.GetFatBlocks<MySpaceProjector>())
            {
                var block = projector.ProjectedGrid?.CubeBlocks.FirstOrDefault(b =>
                    b.BlockDefinition.Id.SubtypeName == subtype
                    && projector.CanBuild(b, true) == BuildCheckResult.OK
                );
                if (block == null)
                    continue;

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
                return;
            }

            MyLog.Default.WriteLineAndConsole($"ToolProbe: no buildable {subtype}");
        }

        public void Dispose() { }
    }
}
