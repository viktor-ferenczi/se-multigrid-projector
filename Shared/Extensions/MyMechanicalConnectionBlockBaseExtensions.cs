using System.Reflection;
using HarmonyLib;
using MultigridProjector.Utilities;
using Sandbox.Definitions;
using Sandbox.Game.Entities.Blocks;

namespace MultigridProjector.Extensions
{
    public static class MyMechanicalConnectionBlockBaseExtensions
    {
        // CallAttach is plain (non-virtual) protected, so the runtime publicizer exposes it and
        // callers invoke it directly. Attach is protected *virtual*, which the Pulsar/Magnetar
        // source-compile publicizer leaves protected (changing a virtual member's accessibility
        // would break override chains), so it must still be reached by reflection. The reflection
        // call is also relied upon by BuildMissingHead, which catches the resulting
        // TargetInvocationException to swallow a known NullReferenceException.
        private static readonly MethodInfo AttachMethodInfo = Validation.EnsureInfo(AccessTools.DeclaredMethod(typeof(MyMechanicalConnectionBlockBase), "Attach", new[] {typeof(MyAttachableTopBlockBase), typeof(bool)}));
        public static void Attach(this MyMechanicalConnectionBlockBase obj, MyAttachableTopBlockBase topBlock, bool updateGroup = true)
        {
            AttachMethodInfo.Invoke(obj, new object[] {topBlock, updateGroup});
        }

        // Adapts the game's CreateTopPart(out topBlock, ...) to a return value and fills in the
        // base block's BuiltBy as the builder id.
        public static MyAttachableTopBlockBase CreateTopPart(this MyMechanicalConnectionBlockBase baseBlock, MyCubeBlockDefinitionGroup definitionGroup, MyMechanicalConnectionBlockBase.MyTopBlockSize topSize, bool instantBuild)
        {
            baseBlock.CreateTopPart(out var topBlock, baseBlock.BuiltBy, definitionGroup, topSize, instantBuild);
            return topBlock;
        }
    }
}
