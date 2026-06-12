using Sandbox.Graphics.GUI;
using System;
using System.Collections.Generic;
using ClientPlugin.Settings.Tools;
using VRage.Game;
using VRageMath;

namespace ClientPlugin.Settings.Elements;

internal class ColorAttribute : Attribute, IElement
{
    public readonly bool HasAlpha;
    public readonly string Label;
    public readonly string Description;

    private Color originalBorderColor;

    public ColorAttribute(bool hasAlpha = false, string label = null, string description = null)
    {
        HasAlpha = hasAlpha;
        Label = label;
        Description = description;
    }

    public List<Control> GetControls(string name, Func<object> propertyGetter, Action<object> propertySetter)
    {
        var defaultColor = (Color)propertyGetter();
        var defaultColorHex = HasAlpha ? defaultColor.ToHexStringRgba() : defaultColor.ToHexStringRgb();

        var sample = new MyGuiControlButton(visualStyle: MyGuiControlButtonStyleEnum.SquareSmall)
        {
            CanHaveFocus = false,
            BorderColor = defaultColor,
            BorderEnabled = true,
            BorderSize = 20
        };

        var textBox = new MyGuiControlTextbox(defaultText: defaultColorHex, maxLength: HasAlpha ? 8 : 6)
        {
            Size = new Vector2(0.1f, 0.04f)
        };

        originalBorderColor = textBox.BorderColor;

        textBox.TextChanged += box =>
        {
            if (HasAlpha ? box.Text.TryParseColorFromHexRgba(out var color) : box.Text.TryParseColorFromHexRgb(out color))
            {
                box.BorderColor = originalBorderColor;
                box.BorderEnabled = false;

                sample.BorderColor = color;
                    
                if (color != PropertyGetter())
                    PropertySetter(color);
                    
                var text = HasAlpha ? color.ToHexStringRgba() : color.ToHexStringRgb();
                if (text != box.Text)
                    box.Text = text;
            }
            else
            {
                box.BorderColor = Color.Red;
                box.BorderEnabled = true;
            }
        };

        textBox.SetToolTip(Description);

        var label = Tools.Tools.GetLabelOrDefault(name, Label);
        return new List<Control>()
        {
            new Control(new MyGuiControlLabel(text: label), minWidth: Control.LabelMinWidth),
            new Control(sample, offset: new Vector2(0f, 0.005f)),
            new Control(textBox, fixedWidth: textBox.Size.X),
        };

        void PropertySetter(Color color) => propertySetter(color);
        Color PropertyGetter() => (Color)propertyGetter();
    }

    public List<Type> SupportedTypes { get; } = new List<Type>()
    {
        typeof(Color)
    };
}