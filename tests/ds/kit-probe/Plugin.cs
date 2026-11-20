using System.Collections.Generic;
using Sandbox.Game.Entities;
using Sandbox.Game.World;
using VRage;
using VRage.Game;
using VRage.ObjectBuilders;
using VRage.Plugins;
using VRage.Utils;

namespace KitProbe
{
    // Test only, for test_anticheat_ds.py: puts steel plates into the inventory of every
    // player's character on the server, once per character. A survival player who isn't an
    // admin can't get items otherwise, and since 1.211.018 a projected block is built only
    // for a builder holding its first component, which is a steel plate for the blocks there.
    // ReSharper disable once UnusedType.Global
    public class Plugin : IPlugin
    {
        private const int SteelPlates = 50;

        private readonly HashSet<long> stocked = new HashSet<long>();
        private int tick;

        public void Init(object gameInstance) { }

        public void Update()
        {
            if (++tick % 60 != 0 || MySession.Static?.Players == null)
                return;

            foreach (var player in MySession.Static.Players.GetOnlinePlayers())
            {
                var character = player.Character;
                if (character == null || character.IsDead || !stocked.Add(character.EntityId))
                    continue;

                var plate = MyObjectBuilderSerializer.CreateNewObject<MyObjectBuilder_Component>(
                    "SteelPlate"
                );
                character.GetInventory().AddItems(SteelPlates, plate);
                MyLog.Default.WriteLineAndConsole(
                    $"KitProbe: gave {SteelPlates} steel plates to {player.DisplayName}"
                );
            }
        }

        public void Dispose() { }
    }
}
