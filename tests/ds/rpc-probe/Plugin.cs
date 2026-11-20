using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text;
using Entities.Blocks;
using Sandbox.Engine.Multiplayer;
using Sandbox.Game.Entities.Blocks;
using Sandbox.Game.Gui;
using Sandbox.Game.Screens.Terminal.Controls;
using Sandbox.Game.World;
using Sandbox.ModAPI;
using VRage.Plugins;
using VRage.Utils;
using VRageMath;

namespace RpcProbe
{
    // Test only, for test_build_checks_ds.py: a projector action that sends the vanilla
    // BuildInternal RPC to the server with the arguments named in the projector's custom data,
    // one key=value per line:
    //
    //   subtype=LargeStator   the first projected block of this subtype the projector can build
    //   builder=self          self: the local character, projector: the projector itself
    //   builtBy=self          self: the local identity, other: another identity
    //   instant=true          requestInstant
    //
    // An honest client sends builder=self, builtBy=self.
    // ReSharper disable once UnusedType.Global
    public class Plugin : IPlugin
    {
        public const string ActionId = "MgpTestBuildRpc";

        private static readonly MethodInfo BuildInternal = typeof(MyProjectorBase).GetMethod(
            "BuildInternal",
            BindingFlags.Instance | BindingFlags.NonPublic
        );

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

            MyTerminalControlFactory.AddAction(
                new MyTerminalAction<MySpaceProjector>(
                    ActionId,
                    new StringBuilder("Send a BuildInternal RPC (test)"),
                    Send,
                    MyTerminalActionIcons.TOGGLE
                )
            );
            added = true;
            MyLog.Default.WriteLineAndConsole("RpcProbe: action added");
        }

        private static void Send(MySpaceProjector projector)
        {
            try
            {
                var args = projector
                    .CustomData.Split('\n')
                    .Select(line => line.Trim().Split(new[] { '=' }, 2))
                    .Where(pair => pair.Length == 2)
                    .ToDictionary(pair => pair[0], pair => pair[1]);

                var subtype = args["subtype"];
                var block = projector.ProjectedGrid?.CubeBlocks.FirstOrDefault(b =>
                    b.BlockDefinition.Id.SubtypeName == subtype
                    && projector.CanBuild(b, true) == BuildCheckResult.OK
                );
                if (block == null)
                {
                    MyLog.Default.WriteLineAndConsole($"RpcProbe: no buildable {subtype}");
                    return;
                }

                var identity = MySession.Static.LocalPlayerId;
                var builder =
                    args["builder"] == "projector"
                        ? projector.EntityId
                        : MySession.Static.LocalCharacter.EntityId;
                var builtBy = args["builtBy"] == "other" ? identity + 1 : identity;
                var instant = bool.Parse(args["instant"]);

                MyMultiplayer.RaiseEvent(
                    (MyProjectorBase)projector,
                    p =>
                        (Action<Vector3I, long, long, bool, long>)
                            Delegate.CreateDelegate(
                                typeof(Action<Vector3I, long, long, bool, long>),
                                p,
                                BuildInternal
                            ),
                    block.Position,
                    identity,
                    builder,
                    instant,
                    builtBy
                );
                MyLog.Default.WriteLineAndConsole(
                    $"RpcProbe: sent {subtype} at {block.Position} builder={builder} builtBy={builtBy} instant={instant}"
                );
            }
            catch (Exception e)
            {
                MyLog.Default.WriteLineAndConsole($"RpcProbe: failed: {e}");
            }
        }

        public void Dispose() { }
    }
}
