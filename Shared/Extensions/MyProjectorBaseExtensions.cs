using System.Collections.Generic;
using Sandbox.Definitions;
using Sandbox.Game.Entities;
using Sandbox.Game.Entities.Blocks;
using Sandbox.Game.Entities.Cube;
using VRage.Game;
using VRageMath;

namespace MultigridProjector.Extensions
{
    // The projector's internal members are reached directly thanks to the Krafs publicizer.
    // Game methods that became public (IsProjecting, RemoveProjection, SendNewBlueprint,
    // UpdateSounds, UpdateText, SetTransparency, SetRotation, CheckMissingDlcs,
    // RequestRemoveProjection, MyProjector_IsWorkingChanged) are now called on the instance
    // directly, so no wrapper extensions are needed for them.
    public static class MyProjectorBaseExtensions
    {
        public static MyProjectorClipboard GetClipboard(this MyProjectorBase projector)
        {
            return projector.Clipboard;
        }

        public static void SetBuildableBlocksCount(this MyProjectorBase projector, int value)
        {
            projector.m_buildableBlocksCount = value;
        }

        public static bool GetShowOnlyBuildable(this MyProjectorBase projector)
        {
            return projector.m_showOnlyBuildable;
        }

        public static bool GetKeepProjection(this MyProjectorBase projector)
        {
            return projector.m_keepProjection;
        }

        public static bool GetInstantBuildingEnabled(this MyProjectorBase projector)
        {
            return projector.m_instantBuildingEnabled;
        }

        public static bool GetShouldUpdateTexts(this MyProjectorBase projector)
        {
            return projector.m_shouldUpdateTexts;
        }

        public static void SetShouldUpdateTexts(this MyProjectorBase projector, bool value)
        {
            projector.m_shouldUpdateTexts = value;
        }

        public static void SetRemainingBlocks(this MyProjectorBase projector, int value)
        {
            projector.m_remainingBlocks = value;
        }

        public static void SetStatsDirty(this MyProjectorBase projector, bool value)
        {
            projector.m_statsDirty = value;
        }

        public static void SetTotalBlocks(this MyProjectorBase projector, int value)
        {
            projector.m_totalBlocks = value;
        }

        public static void SetRemainingArmorBlocks(this MyProjectorBase projector, int value)
        {
            projector.m_remainingArmorBlocks = value;
        }

        public static int GetRemainingArmorBlocks(this MyProjectorBase projector)
        {
            return projector.m_remainingArmorBlocks;
        }

        public static Dictionary<MyCubeBlockDefinition, int> GetRemainingBlocksPerType(this MyProjectorBase projector)
        {
            return projector.m_remainingBlocksPerType;
        }

        public static List<MyObjectBuilder_CubeGrid> GetOriginalGridBuilders(this MyProjectorBase projector)
        {
            return projector.m_originalGridBuilders;
        }

        public static void SetOriginalGridBuilders(this MyProjectorBase projector, List<MyObjectBuilder_CubeGrid> gridBuilders)
        {
            projector.m_originalGridBuilders = gridBuilders;
        }

        public static int GetProjectionTimer(this MyProjectorBase projector)
        {
            return projector.m_projectionTimer;
        }

        public static void SetProjectionTimer(this MyProjectorBase projector, int value)
        {
            projector.m_projectionTimer = value;
        }

        public static void SetHiddenBlock(this MyProjectorBase projector, MySlimBlock block)
        {
            projector.m_hiddenBlock = block;
        }

        public static bool GetTierCanProject(this MyProjectorBase projector)
        {
            return projector.m_tierCanProject;
        }

        public static bool GetRemoveRequested(this MyProjectorBase projector)
        {
            return projector.m_removeRequested;
        }

        public static void SetRemoveRequested(this MyProjectorBase projector, bool value)
        {
            projector.m_removeRequested = value;
        }

        public static bool GetShouldResetBuildable(this MyProjectorBase projector)
        {
            return projector.m_shouldResetBuildable;
        }

        public static void SetShouldResetBuildable(this MyProjectorBase projector, bool value)
        {
            projector.m_shouldResetBuildable = value;
        }

        public static bool GetForceUpdateProjection(this MyProjectorBase projector)
        {
            return projector.m_forceUpdateProjection;
        }

        public static void SetForceUpdateProjection(this MyProjectorBase projector, bool value)
        {
            projector.m_forceUpdateProjection = value;
        }

        public static bool GetShouldUpdateProjection(this MyProjectorBase projector)
        {
            return projector.m_shouldUpdateProjection;
        }

        public static void SetShouldUpdateProjection(this MyProjectorBase projector, bool value)
        {
            projector.m_shouldUpdateProjection = value;
        }

        public static int GetLastUpdate(this MyProjectorBase projector)
        {
            return projector.m_lastUpdate;
        }

        public static void SetLastUpdate(this MyProjectorBase projector, int value)
        {
            projector.m_lastUpdate = value;
        }

        public static Vector3I GetProjectionRotation(this MyProjectorBase projector)
        {
            return projector.m_projectionRotation;
        }

        public static void SetIsActivating(this MyProjectorBase projector, bool value)
        {
            projector.IsActivating = value;
        }

        public static void RemapObjectBuilders(this MyProjectorBase projector)
        {
            var gridBuilders = projector.GetOriginalGridBuilders();
            if (gridBuilders == null || gridBuilders.Count <= 0)
                return;

            // Consistent remapping of all grids to keep sub-grid relations intact
            lock (gridBuilders)
                MyEntities.RemapObjectBuilderCollection(gridBuilders);
        }
    }
}
