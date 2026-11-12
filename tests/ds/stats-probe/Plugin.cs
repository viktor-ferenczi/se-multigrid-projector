using Sandbox.Engine;
using VRage.Library.Utils;
using VRage.Plugins;

namespace StatsProbe
{
    // Test only, for test_havok_leak_ds.py: the game logs its statistics, the MEMORY VALUES
    // line with the Havok memory among them, every 2 seconds instead of once a minute.
    // ReSharper disable once UnusedType.Global
    public class Plugin : IPlugin
    {
        public void Init(object gameInstance)
        {
            MyGeneralStats.Static.LogInterval = MyTimeSpan.FromSeconds(2);
        }

        public void Update() { }

        public void Dispose() { }
    }
}
