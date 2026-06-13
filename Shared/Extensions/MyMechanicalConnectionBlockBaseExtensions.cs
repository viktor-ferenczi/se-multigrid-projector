using Sandbox.Definitions;
using Sandbox.Game.Entities.Blocks;

namespace MultigridProjector.Extensions
{
    public static class MyMechanicalConnectionBlockBaseExtensions
    {
        // CallAttach and Attach are now public on MyMechanicalConnectionBlockBase (via the
        // publicizer), so callers invoke them directly without reflection wrappers.

        // Adapts the game's CreateTopPart(out topBlock, ...) to a return value and fills in the
        // base block's BuiltBy as the builder id.
        public static MyAttachableTopBlockBase CreateTopPart(this MyMechanicalConnectionBlockBase baseBlock, MyCubeBlockDefinitionGroup definitionGroup, MyMechanicalConnectionBlockBase.MyTopBlockSize topSize, bool instantBuild)
        {
            baseBlock.CreateTopPart(out var topBlock, baseBlock.BuiltBy, definitionGroup, topSize, instantBuild);
            return topBlock;
        }
    }
}
