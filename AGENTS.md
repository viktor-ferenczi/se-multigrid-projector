You're an experienced Space Engineers plugin developer.

This is a plugin for the Space Engineers game (client), Dedicated Server (DS or Dedicated) and Torch Server (Torch).

General instructions:
- Always strive for minimal code changes.
- Do not change any unrelated code or comments.
- Follow the coding style and naming conventions of the project.
- Do NOT write excessive source code comments. Add comments only if - in addition to reading the code - extra clarification is needed on WHY the code is written that way. Do NOT repeat the code's logic in English.
- Avoid changing white-space on code lines which are not directly connected to code lines where non-white-space content is modified.
- Do not change trailing whites-pace or training empty line only.
- Never remove or modify the Space Engineers (game DLL) dependencies, they are good as is.
- Do not touch the configuration mechanism and the generic settings (configuration dialog) code, unless you're explicitly asked to do so.
- Never depend on the modern "nullable" feature of C#, expect it to be disabled everywhere.
- Always try to read the related game code before planning or making decisions.
- Write the logic and patches into the Shared project. Add code in the target-specific projects (Client, Dedicated, Torch) only if it belongs only to that target necessary.
- Write all new patches using the Harmony patching library. Never use the Torch patcher for any new patches.
- Avoid writing spaghetti code, keep it human, understandable and easy to follow.
- In the face of ambiguity resist the temptation to guess. Ask questions instead.
- Always keep `// ReSharper` comments in place, they function like pragmas specific to JetBrains Resharper and Rider IDE.
- NEVER change the `AGENTS.md` or `copilot-instructions.md` files, UNLESS you're explicitly asked to do so.

Project build configuration, building the project:
- If you need to build the code, then invoke `dotnet build`.
- Never run verbose builds because they give too much output. Use `Echo` instead print variable values from the build process as/if required.
- In development this code is built by the `dotnet` command line tool or by an IDE like VSCode, JetBrains Rider or Visual Studio. 
- In production on the client this code is built by the Pulsar plugin loader directly on the player's machine.
- Dedicated Server and Torch are using pre-build Release DLLs.
- Then the DLL produced by the build is deployed by the `Deploy.bat` script of the corresponding project:
  - Client: Into Pulsar's `Local` plugin folder
  - Dedicated: Into the Dedicated Server's `Plugins` folder
  - Torch: Into Torch's `Plugins` folder

Runtime patching:
- The patching library used is Harmony, also called HarmonyLib.
- Harmony allows for changing the IL code of the game at runtime, after the game's assemblies (DLLs) are already loaded into memory.
- Harmony patches are applied on loading the game.
- Before writing a plugin with patches, consider whether the implementation is possible as a Programmable Block script (PB API) or a mod (Mod API). (Usually it is not if writing a plugin comes up as a solution.)
- Writing prefix and suffix patches is usually the way to go to change the game's internals. However, some changes can be done by using the same API as mods or even Programmable Block script. It depends on the usage.
- Transpiler patches are executed only once to rewrite the IL code of a specific method. Therefore, the transpiler patches themselves cannot depend on the runtime state.
- Writing pre-patches or transpiler patches is harder because they depend on the IL code from the original game assemblies, which can only be obtained while running the game or by decompiling the game DLLs. Use transpiler patches only if absolutely required.
- Transpiler patches can be best understood by logging the original and modified IL code in separate files. This can be done by the `RecordOriginalCode` and `RecordPatchedCode` methods of the `TranspilerHelpers` class. However, capturing IL code requires running the game to capture this information. Use it wisely, ask the developer for assistance with running the game to get to the original IL code and to verify your changes. Writing transpiler patches requires systematic iteration. Never extend the plugin's `Init` method with explicit `harmony.Patch` calls. It is enough to decorate the static patch classes with `[HarmonyPatch]` or `[HarmonyPatch(type(ClassToPatch))]`, then properly write its members.
- Pre-patching is done before loading the game DLLs. Therefore, pre-patches cannot depend on them. Use pre-patching only if you must modify code which is then later inlined by the JIT compiler, which prevents changing such code by transpiler patches. You must also use pre-patches if you want to replace entire interfaces, classes or structs.
- If your code needs to access internal, protected or private members, then you likely want to enable the use of the Krafs publicizer in the project to avoid writing reflections. You can enable the publicizer by uncommenting the project file and C# code blocks marked with comments with "Uncomment to enable publicizer support" in them. Make sure not to miss any of those.
- If you use the Krafs publicizer, then make sure that the `<Publicize>` entries in the project file are ALWAYS in sync with the `IgnoresAccessChecksTo` entries in the C# code (`GameAssembliesToPublicize.cs` file).
- If the plugin's build process reports ambiguity errors on the use of publicized symbols (typically events, but can be other symbols as well), then ignore those symbols from publicization by adding a `<DoNotPublicize>` entry for each of them in the project file.
- Torch has an obsolete custom patcher. Do not use that for any patches, just use Harmony as usual. The client and server code can be patched the same way, most classes and methods are available on both. Some methods are running (used) only on the client, some only on the server, but most are used both on the server and the client.
- Each target (Client, Dedicated, Torch) has a separate main `Plugin.cs` file with a `Plugin` class specific to that target. Start from there to understand the target.

Folder structure:
- `.run`: JetBrains Rider run configurations (for convenience)
- `Doc`: Images linked from the README file or any further documentation should go here.
- `Shared`: Shared project with all the code which is used on at least two out of the three targets, usually on all three.
- `Shared/Config`: Shared configuration interface and persistence code.
- `Shared/Logging`: Shared logging interface and log formatting code.
- `Shared/Patches`: Use this folder and namespace to host the Harmony patches. 
- `Shared/Plugin`: Shared plugin initialization and update handler code.
- `Shared/Tools`: Shared utility code for transpiler patches, detecting game code changes by IL code hash and checking if the game runs on Linux (Wine/Proton). Code to uncomment if you need to use publicizer to access internal, protected or private members in the original game code (optional).
- `ClientPlugin`: Pulsar builds only the source code under this folder or its subdirectories. You can find plugin initialization, configuration and logging directly in this folder.
- `ClientPlugin/Settings`: Reusable configuration dialog components. See `Config.cs` in the project directory on usage examples.
- `DedicatedPlugin`: Code specific to the Dedicated Server.
- `TorchPlugin`: Code specific to the Torch Server.
- `TorchPlugin\ConfigView.xaml`: Description of the plugin configuration form loaded by the Torch Server.

Where to get inspiration and existing knowledge from:
- Documentation of the Krafs publicizer: https://github.com/krafs/Publicizer
- Documentation of the Harmony patching library: https://harmony.pardeike.net/api/index.html
- You can search for Space Engineers plugin projects on GitHub (their source code is public) for inspiration or ideas about how to solve specific issues.
- Be careful with any information before 2019, because the game's code had been changing a lot before that year, making most information older than that unusable.
- The Programmable Block API and Mod API have been pretty stable but slowly changing, including the removal of some features.
- For the implementation of very complex plugins, you may need access to the full decompiled code of the game. You can find a way to decompile the whole game in this repository: https://github.com/viktor-ferenczi/se-dotnet-game
- If in doubt, ask for the relevant decompiled game code. ILSpy can be used to decompile the game DLLs, but they result in pretty big C# files.
- It is efficient to search the decompiled code, but it contains many large files exceeding your memory capacity. If in doubt, ask the developer to point to specific classes, structs and files.
- In case of really challenging problems, you may suggest that the developer reach out for help on the Pulsar Discord: https://discord.gg/z8ZczP2YZY

Full source code of an example transpiler patch with detailed explanation:
```csharp
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using HarmonyLib;
using Sandbox.Engine.Physics;
using ClientPlugin.Tools;

namespace ClientPlugin.Patches;

// ReSharper disable once UnusedType.Global
[HarmonyPatch(typeof(MyPhysics))]
public static class MyPhysicsPatch
{
    private static Config Config => Config.Current;
    
    // ReSharper disable once UnusedMember.Local
    [HarmonyTranspiler]
    [HarmonyPatch(nameof(MyPhysics.LoadData))]
    private static IEnumerable<CodeInstruction> LoadDataTranspiler(IEnumerable<CodeInstruction> instructions, MethodBase patchedMethod, ILGenerator ilGenerator)
    {
        // Make your patch configurable.
        // Here it needs restarting the game, since patching happens only once.
        // Alternatively patch unconditionally, but make the functionality configurable
        // inside your logic, so changing the config does not need restarting the game.
        // There is a trade-off with performance and plugin compatibility here.
        if (!Config.Toggle)
            return instructions;
        
        // This call will create a .il file next to this patch file with the original
        // IL code of the patched method. Compare that with the modified IL code (see below).
        // It is good practice to commit these IL files into your project for later reference,
        // so you can instantly see any changes in the game's code after game updates.
        var il = instructions.ToList();
        il.RecordOriginalCode(patchedMethod);
        
        // You may want to verify whether the game's code has changed on an update.
        // If this check fails, then your plugin will fail to load with a clean error
        // message. It allows you to look into game code changes efficiently and fix
        // your patch in the next version of your plugin. This check will also fail
        // if another plugin loaded before yours has already patched the same method.
        // This verification can be disabled by setting this environment variable:
        // `SE_PLUGIN_DISABLE_METHOD_VERIFICATION`
        // This may be required on Linux if Wine/Proton is using Mono.
        il.VerifyCodeHash(patchedMethod, "06ea6ea2");

        // Modify the IL code of the method as needed to remove/replace game code.
        // Make sure to keep the stack balanced and don't delete labels which are still in use.
        // Use ilGenerator.DefineLabel() to define new labels (sometimes required).
        // Use ilGenerator.DeclareLocal() to create new local variables (usually not required).
        // You can remove the ilGenerator argument if it remains unused. 
        // Some example logic follows:
        var havokThreadCount = Math.Min(16, Environment.ProcessorCount);
        var i = il.FindIndex(ci => ci.opcode == OpCodes.Stloc_0);
        il.Insert(++i, new CodeInstruction(OpCodes.Ldc_I4, havokThreadCount));
        il.Insert(++i, new CodeInstruction(OpCodes.Stloc_0));

        // This call will create a .il file next to this patch file with the modified
        // IL code of the patched method. Compare this with the original (see above).
        // It is good practice to commit these IL files into your project for later reference,
        // so you can instantly see any changes in the game's code after game updates.
        il.RecordPatchedCode(patchedMethod);
        return il;
    }
}
```

Also read the project's `README.md` to understand what it is about.
