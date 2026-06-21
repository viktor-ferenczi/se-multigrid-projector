using Sandbox.Graphics.GUI;
using VRage.Utils;
using VRageMath;

namespace ClientPlugin.Settings.Elements;

internal class Control
{
    // FIXME: This is global and not determined automatically
    public static readonly float LabelMinWidth = 0.18f;

    public readonly MyGuiControlBase GuiControl;
    public readonly float? FixedWidth;
    public readonly float MinWidth;
    public readonly float? FillFactor;
    public readonly MyGuiDrawAlignEnum OriginAlign;
    public readonly Vector2 Offset;
    public readonly float RightMargin;

    public Control(MyGuiControlBase guiControl, float? fixedWidth = null, float minWidth = 0f, float? fillFactor = null, MyGuiDrawAlignEnum originAlign = MyGuiDrawAlignEnum.HORISONTAL_LEFT_AND_VERTICAL_CENTER, Vector2? offset = null, float rightMargin = 0f)
    {
        GuiControl = guiControl;
        FixedWidth = fixedWidth;
        MinWidth = minWidth;
        FillFactor = fillFactor;
        OriginAlign = originAlign;
        Offset = offset ?? Vector2.Zero;
        RightMargin = rightMargin;
    }
}