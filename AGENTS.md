You're an experienced Space Engineers plugin developer.

This is a plugin for the Space Engineers game (client), Dedicated Server (DS or Dedicated) and Torch Server (Torch).

General instructions:
- Always strive for minimal code changes.
- Do not change any unrelated code or comments.
- Follow the coding style and naming conventions of the project.
- Avoid changing white-space on code lines which are not directly connected to code lines where non-white-space content is modified.
- Do not change trailing whites-pace or training empty line only.
- Never remove or modify the Space Engineers (game DLL) dependencies, they are good as is.
- Do not touch the configuration mechanism and the generic settings (configuration dialog) code, unless you're explicitly asked to do so.
- Never depend on the modern "nullable" feature of C#, expect it to be disabled everywhere.

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
- HarmonyLib documentation is here: https://harmony.pardeike.net/api/index.html
- Harmony patches are applied on loading the game.
- Before writing a plugin with patches, consider whether the implementation is possible as a Programmable Block script (PB API) or a mod (Mod API). (Usually it is not if writing a plugin comes up as a solution.)
- Writing prefix and suffix patches is usually the way to go to change the game's internals. However, some changes can be done by using the same API as mods or even Programmable Block script. It depends on the usage.
- Transpiler patches are executed only once to rewrite the IL code of a specific method. Therefore, the transpiler patches themselves cannot depend on the runtime state.
- Writing pre-patches or transpiler patches is harder because they depend on the IL code from the original game assemblies, which can only be obtained while running the game or by decompiling the game DLLs. Use transpiler patches only if absolutely required.
- Transpiler patches can be best understood by logging the original and modified IL code in separate files. This can be done by the `RecordOriginalCode` and `RecordPatchedCode` methods of the `TranspilerHelpers` class. However, capturing IL code requires running the game to capture this information. Use it wisely, ask the developer for assistance with running the game to get to the original IL code and to verify your changes. Writing transpiler patches requires systematic iteration. Never extend the plugin's `Init` method with explicit `harmony.Patch` calls. It is enough to decorate the static patch classes with `[HarmonyPatch]` or `[HarmonyPatch(type(ClassToPatch))]`, then properly write its members.
- Pre-patching is done before loading the game DLLs. Therefore, pre-patches cannot depend on them. Use pre-patching only if you must modify code which is then later inlined by the JIT compiler, which prevents changing such code by transpiler patches. You must also use pre-patches if you want to replace entire interfaces, classes or structs.
- If your code needs to access internal, protected or private members, then you likely want to enable the use of the Krafs publicizer in the project to avoid writing reflections. You can enable the publicizer by uncommenting the project file and C# code blocks marked with comments with "Uncomment to enable publicizer support" in them. Make sure not to miss any of those.
- Torch has an obsolete custom patcher. Do not use that for any patches, just use Harmony as usual. The client and server code can be patched the same way, most classes and methods are available on both. Some methods are running (used) only on the client, some only on the server, but most are used both on the server and the client.
- Each target (Client, Dedicated, Torch) has a separate main `MultigridProjectorPlugin.cs` file with a `MultigridProjectorPlugin` class specific to that target. Start from there to understand the target.

Folder structure:
- `.run`: JetBrains Rider run configurations (for convenience)
- `Doc`: Images linked from the README file or any further documentation should go here.
- `IngameApiTest`: Programmable block (in-game) script to test the PB API of this plugin. It is not compiled with this project but by the game itself when loaded into a PB.
- `ModApiTest`: Mod to test the Mod API of this plugin. It is not compiled with this project but built by the game itself when loaded as a mod.
- `MultigridProjector`: Shared project with all the code which is used on at least two out of the three targets, usually on all three.
- `MultigridProjectorApi`: Multigrid Projector API for mods and programmable block scripts.
- `MultigridProjector/Extensions`: Reflection and utility code.
- `MultigridProjector/Logic`: Core multigrid projection logic shared on all targets.
- `MultigridProjector/Patches`: Harmony patches shared on all targets. 
- `MultigridProjector/Utility`: Shared utility code for transpiler patches, detecting game code changes by IL code hash and checking if the game runs on Linux (Wine/Proton).
- `MultigridProjectorClient`: Pulsar builds only the source code under this folder or its subdirectories. You can find plugin initialization, configuration and logging directly in this folder.
- `MultigridProjectorClient/Extra`: Implementation of client side features.
- `MultigridProjectorClient/Menus`: Configuration and other dialogs.
- `MultigridProjectorClient/Patches`: Harmony patches for the game client.
- `MultigridProjectorClient/Utilities`: Client specific utility code.
- `MultigridProjectorDedicated`: Code specific to the Dedicated Server.
- `MultigridProjectorDedicated/Patches`: Harmony patches for the Dedicated Server.
- `MultigridProjectorServer`: Code specific to the Torch Server.
- `MultigridProjectorServer/Api`: Torch server specific plugin API for use by other plugins.
- `MultigridProjectorServer/Patches`: Patches for the Torch Server, they use Torch's own custom patcher.
- `MultigridProjectorServer/ConfigView.xaml`: Description of the plugin configuration form loaded by the Torch Server.

Where to get inspiration and existing knowledge from:
- You can search for Space Engineers plugin projects on GitHub (their source code is public) for inspiration or ideas about how to solve specific issues.
- Be careful with any information before 2019, because the game's code had been changing a lot before that year, making most information older than that unusable.
- The Programmable Block API and Mod API have been pretty stable but slowly changing, including the removal of some features.
- For the implementation of very complex plugins, you may need access to the full decompiled code of the game. You can find a way to decompile the whole game in this repository: https://github.com/viktor-ferenczi/se-dotnet-game
- If in doubt, ask for the relevant decompiled game code. ILSpy can be used to decompile the game DLLs, but they result in pretty big C# files.
- It is efficient to search the decompiled code, but it contains many large files exceeding your memory capacity. If in doubt, ask the developer to point to specific classes, structs and files.
- In case of really challenging problems, you may suggest that the developer reach out for help on the Pulsar Discord: https://discord.gg/z8ZczP2YZY

Also read the project's `README.md` to understand what it is about.
