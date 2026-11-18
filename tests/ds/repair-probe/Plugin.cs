using System.Linq;
using System.Text;
using Entities.Blocks;
using Sandbox.Game.Gui;
using Sandbox.Game.Screens.Terminal.Controls;
using Sandbox.Game.World;
using VRage.Plugins;
using VRage.Utils;

namespace RepairProbe
{
    // Test only, for test_repair_projection_ds.py: a projector action that presses MGP's
    // "Load Repair Projection" terminal button, so Remote can press it with its action op.
    // ReSharper disable once UnusedType.Global
    public class Plugin : IPlugin
    {
        public const string ActionId = "MgpTestLoadRepairProjection";

        private bool added;

        public void Init(object gameInstance) { }

        public void Update()
        {
            // GetControls of a type before the game created its controls would register an
            // empty list, and the game would then skip creating them
            if (
                added
                || MySession.Static == null
                || !MyTerminalControlFactory.AreControlsCreated<MySpaceProjector>()
            )
                return;

            // MGP adds its button when the game creates the projector's terminal controls
            var button = MyTerminalControlFactory
                .GetControls(typeof(MySpaceProjector))
                .OfType<MyTerminalControlButton<MySpaceProjector>>()
                .FirstOrDefault(control => control.Id == "RepairProjection");
            if (button == null)
                return;

            MyTerminalControlFactory.AddAction(
                new MyTerminalAction<MySpaceProjector>(
                    ActionId,
                    new StringBuilder("Load Repair Projection (test)"),
                    projector => button.Action(projector),
                    MyTerminalActionIcons.TOGGLE
                )
            );
            added = true;
            MyLog.Default.WriteLineAndConsole("RepairProbe: action added");
        }

        public void Dispose() { }
    }
}
