using MultigridProjector.Logic;
using MultigridProjectorClient.Utilities;
using ClientPlugin;
using MultigridProjectorClient.Extra;
using VRage.Game;
using VRage.Game.Components;

namespace MultigridProjectorClient
{
    // ReSharper disable once UnusedType.Global
    [MySessionComponentDescriptor(MyUpdateOrder.AfterSimulation)]
    public class PluginSession : MySessionComponentBase
    {
        private MultigridProjectorSession mgpSession;

        public override void Init(MyObjectBuilder_SessionComponent sessionComponent)
        {
            MultigridProjection.EnsureNoProjections();

            mgpSession = new MultigridProjectorSession();

            ProjectorAligner.Initialize();
        }

        protected override void UnloadData()
        {
            if (mgpSession != null)
            {
                mgpSession.Dispose();
                mgpSession = null;
            }

            MultigridProjection.EnsureNoProjections();

            if (Config.Current.ProjectorAligner)
            {
                ProjectorAligner.Instance?.Dispose();
            }
        }

        public override void UpdateAfterSimulation()
        {
            mgpSession?.Update();

            if (Config.Current.BlockHighlight)
                BlockHighlight.HighlightLoop();

            if (Config.Current.ShipWelding)
                ShipWelding.WeldLoop();
        }
    }
}