using System.Collections.Generic;
using System.Text;
using Sandbox.Game.Entities.Cube;
using Sandbox.Game.GameSystems;

namespace MultigridProjector.Extensions
{
    public static class MyBlockGroupExtensions
    {
        public static HashSet<MyTerminalBlock> GetTerminalBlocks(this MyBlockGroup blockGroup)
        {
            return blockGroup.Blocks;
        }

        public static MyBlockGroup NewBlockGroup(string name)
        {
            return new MyBlockGroup
            {
                Name = new StringBuilder(name)
            };
        }
    }
}
