using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;

namespace MultigridProjector.Utilities
{
    // Applies the plugin's Harmony patches and logs exactly which game methods were patched, so a
    // test run can be verified from the log alone. Lives in the Shared project, so both the client
    // (Pulsar) and the dedicated server (Magnetar) plugins use it.
    //
    // The per-patch lines are logged at Info, not Debug, on purpose: the game's MyLog.Default.Debug
    // is [Conditional("DEBUG")] and is therefore compiled out of the Release builds that ship to
    // Magnetar and Pulsar. Info is the lowest level that survives into the build users actually run,
    // so it is the only level at which patch application can be verified from the logs.
    // ReSharper disable once UnusedType.Global
    public static class PatchHelpers
    {
        // Harmony patch category for patches that must be deferred to IPlugin.Init because their
        // target type lives in an assembly not yet loaded at the dedicated server's early bootstrap
        // point. Every patch without this category is applied early, before world load. No patch
        // currently needs this (all targets live in Sandbox.Game, which is loaded long before the
        // bootstrap hook runs), but the mechanism is kept so a future patch against a late-loaded
        // assembly can opt in with [HarmonyPatchCategory(PatchHelpers.LateCategory)] and be applied
        // from Init instead of early.
        public const string LateCategory = "Late";

        // Applies every patch in the executing assembly. Used by the client, whose IPlugin.Init
        // already runs before world load, so there is nothing to gain by splitting into phases.
        public static void PatchAll(Harmony harmony)
        {
            ApplyAndLog(harmony, () => harmony.PatchAll(Assembly.GetExecutingAssembly()), "all patches");
        }

        // Applies the uncategorized patches: everything except the deferred "Late" category. Used by
        // the dedicated server's early bootstrap, before world-load compilation.
        public static void PatchUncategorized(Harmony harmony)
        {
            ApplyAndLog(harmony, () => harmony.PatchAllUncategorized(Assembly.GetExecutingAssembly()), "uncategorized patches");
        }

        // Applies only the patches in the given category. Used by the dedicated server from
        // IPlugin.Init, once the world/session has loaded and any late-loaded target assemblies exist.
        public static void PatchCategory(Harmony harmony, string category)
        {
            ApplyAndLog(harmony, () => harmony.PatchCategory(Assembly.GetExecutingAssembly(), category), $"category '{category}'");
        }

        // Snapshot the methods this Harmony id has already patched, apply, then report exactly the
        // ones this phase added. GetPatchedMethods() is scoped to harmony.Id; the dedicated server
        // applies patches in two phases under the same id (uncategorized early, then the "Late"
        // category from Init), so a before/after delta isolates the current phase.
        private static void ApplyAndLog(Harmony harmony, Action apply, string what)
        {
            var before = new HashSet<MethodBase>(harmony.GetPatchedMethods());
            apply();
            LogAppliedPatches(harmony, before, what);
        }

        // Proof the patches were applied: info-log every game method this phase patched (each with
        // the plugin patch class targeting it) with a running count, then a summary line with the
        // total. A test run can be verified from the log by confirming every expected patch appears.
        private static void LogAppliedPatches(Harmony harmony, HashSet<MethodBase> before, string what)
        {
            var applied = harmony.GetPatchedMethods()
                .Where(method => !before.Contains(method))
                .OrderBy(method => method.DeclaringType?.FullName, StringComparer.Ordinal)
                .ThenBy(method => method.ToString(), StringComparer.Ordinal)
                .ToList();

            var count = 0;
            foreach (var method in applied)
                PluginLog.Info($"Patch applied #{++count}: {DescribePatchedMethod(harmony, method)}");

            PluginLog.Info($"Applied {count} {(count == 1 ? "patch" : "patches")} ({what})");
        }

        // Renders a patched game method as "Namespace.Type.Method(argTypes) <- PatchClass[, ...]",
        // naming the plugin patch classes (filtered to this Harmony id) whose prefix/postfix/
        // transpiler/finalizer targets it.
        private static string DescribePatchedMethod(Harmony harmony, MethodBase method)
        {
            var parameters = string.Join(", ", method.GetParameters().Select(parameter => parameter.ParameterType.Name));
            var target = $"{method.DeclaringType?.FullName}.{method.Name}({parameters})";

            var info = Harmony.GetPatchInfo(method);
            if (info == null)
                return target;

            var patchClasses = info.Prefixes
                .Concat(info.Postfixes)
                .Concat(info.Transpilers)
                .Concat(info.Finalizers)
                .Where(patch => patch.owner == harmony.Id)
                .Select(patch => patch.PatchMethod.DeclaringType?.Name)
                .Distinct()
                .ToList();

            return patchClasses.Count == 0 ? target : $"{target} <- {string.Join(", ", patchClasses)}";
        }
    }
}
