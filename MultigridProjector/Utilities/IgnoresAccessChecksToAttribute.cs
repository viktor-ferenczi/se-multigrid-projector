// Define the IgnoresAccessChecksToAttribute class required to use publicized assemblies at runtime.
// Define the class only if the project is built by Plugin Loader, because the Krafs.Publicizer
// provides this already if the project is built directly in an IDE or by running msbuild.
#if !DEV_BUILD

namespace System.Runtime.CompilerServices
{
    
    /* Uncomment to enable publicizer support
     
    // This code is required in "production" when Pulsar builds the plugin
    [AttributeUsage(AttributeTargets.Assembly, AllowMultiple = true)]
    public sealed class IgnoresAccessChecksToAttribute : Attribute
    {
        public IgnoresAccessChecksToAttribute(string assemblyName)
        {
            AssemblyName = assemblyName;
        }

        public string AssemblyName { get; }
    }
    
    */
    
}

#endif
