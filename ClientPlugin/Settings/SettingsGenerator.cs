using ClientPlugin.Settings.Elements;
using ClientPlugin.Settings.Layouts;
using Sandbox.Graphics.GUI;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Linq.Expressions;
using System.Reflection;


namespace ClientPlugin.Settings;

internal class AttributeInfo
{
    public IElement ElementType;
    public string Name;
    public Func<object> Getter;
    public Action<object> Setter;
}

internal class SettingsGenerator
{
    public readonly string Name;

    private readonly List<AttributeInfo> attributes;
    private List<List<Control>> controls;
    public SettingsScreen Dialog { get; private set; }
    public Layout ActiveLayout { get; private set; }

    private static bool ValidateType(Type type, List<Type> typesList)
    {
        return typesList.Any(t => t.IsAssignableFrom(type));
    }

    private static Delegate GetDelegate(MethodInfo methodInfo)
    {
        // Reconstruct the type
        Type[] methodArgs = methodInfo.GetParameters().Select(p => p.ParameterType).ToArray();
        Type type = Expression.GetDelegateType(methodArgs.Concat(new[] { methodInfo.ReturnType }).ToArray());

        // Create a delegate
        return Delegate.CreateDelegate(type, null, methodInfo);
    }

    public SettingsGenerator()
    {
        attributes = ExtractAttributes();
        Name = Config.Current.Title;
        ActiveLayout = new None(()=>controls);
        Dialog = new SettingsScreen(Name, OnRecreateControls, size: ActiveLayout.SettingsPanelSize);
    }

    private List<MyGuiControlBase> OnRecreateControls()
    {
        CreateConfigControls();
        var controlsToRecreate = ActiveLayout.RecreateControls();
        ActiveLayout.LayoutControls();
        return controlsToRecreate;
    }

    public void SetLayout<T>() where T : Layout
    {
        ActiveLayout = (T)Activator.CreateInstance(typeof(T), (Func<List<List<Control>>>)(() => controls));
        Dialog.UpdateSize(ActiveLayout.SettingsPanelSize);
    }

    public void RefreshLayout()
    {
        ActiveLayout.LayoutControls();
    }

    private void CreateConfigControls()
    {
        controls = new List<List<Control>>();

        foreach (AttributeInfo info in attributes)
        {
            controls.Add(info.ElementType.GetControls(info.Name, info.Getter, info.Setter));
        }
    }

    private static List<AttributeInfo> ExtractAttributes()
    {
        var config = new List<AttributeInfo>();

        foreach (var propertyInfo in typeof(Config).GetProperties())
        {
            var name = propertyInfo.Name;
            foreach (var attribute in propertyInfo.GetCustomAttributes())
            {
                if (attribute is IElement element)
                {
                    if (!ValidateType(propertyInfo.PropertyType, element.SupportedTypes))
                    {
                        throw new Exception(
                            $"Element {element.GetType().Name} for {name} expects "
                            + $"{string.Join("/", element.SupportedTypes)} but "
                            + $"recieved {propertyInfo.PropertyType.FullName}");
                    }

                    var info = new AttributeInfo()
                    {
                        ElementType = element,
                        Name = name,
                        Getter = Getter,
                        Setter = Setter
                    };
                    config.Add(info);
                }
            }

            continue;

            object Getter() => propertyInfo.GetValue(Config.Current);
            void Setter(object value) => propertyInfo.SetValue(Config.Current, value);
        }

        foreach (var methodInfo in typeof(Config).GetMethods())
        {
            string name = methodInfo.Name;
            Delegate method = GetDelegate(methodInfo);

            foreach (var attribute in methodInfo.GetCustomAttributes())
            {
                if (attribute is IElement element)
                {
                    if (!ValidateType(typeof(Delegate), element.SupportedTypes))
                    {
                        throw new Exception(
                            $"Element {element.GetType().Name} for {name} expects "
                            + $"{string.Join("/", element.SupportedTypes)} but "
                            + $"recieved {typeof(Delegate).FullName}");
                    }

                    var info = new AttributeInfo()
                    {
                        ElementType = element,
                        Name = name,
                        Getter = () => method,
                        Setter = null
                    };
                    config.Add(info);
                }
            }
        }

        return config;
    }
}