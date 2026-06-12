using Sandbox.Game.Gui;
using Sandbox.Graphics.GUI;
using System;
using System.Collections.Generic;
using System.Reflection;
using System.Text;
using ClientPlugin.Settings.Tools;
using VRage.Game;
using VRage.Input;
using VRage.Utils;
using VRage;
using VRageMath;

namespace ClientPlugin.Settings.Elements;

internal class KeybindAttribute : Attribute, IElement
{
    public readonly string Label;
    public readonly string Description;

    private Func<Binding> propertyGetter;
    private Action<Binding> propertySetter;

    public KeybindAttribute(string label = null, string description = null)
    {
        Label = label;
        Description = description;
    }

    public List<Control> GetControls(string name, Func<object> propertyGetter, Action<object> propertySetter)
    {
        this.propertyGetter = () => (Binding)propertyGetter();
        this.propertySetter = b => propertySetter(b);

        var binding = this.propertyGetter();

        var label = new MyGuiControlLabel(text: Tools.Tools.GetLabelOrDefault(name, Label));

        var ctrl = new MyGuiControlCheckbox(isChecked: binding.Ctrl, toolTip: "Ctrl");
        var alt = new MyGuiControlCheckbox(isChecked: binding.Alt, toolTip: "Alt");
        var shift = new MyGuiControlCheckbox(isChecked: binding.Shift, toolTip: "Shift");
            
        ctrl.IsCheckedChanged += (cb) => {
            var b = this.propertyGetter();
            b.Ctrl = cb.IsChecked;
            this.propertySetter(b);
        };

        alt.IsCheckedChanged += (cb) => {
            var b = this.propertyGetter();
            b.Alt = cb.IsChecked;
            this.propertySetter(b);
        };

        shift.IsCheckedChanged += (cb) => {
            var b = this.propertyGetter();
            b.Shift = cb.IsChecked;
            this.propertySetter(b);
        };

        var control = new MyControl(
            MyStringId.GetOrCompute($"{name.Replace(" ", "")}Keybind"),
            MyStringId.GetOrCompute(name),
            MyGuiControlTypeEnum.General,
            null,
            binding.Key);

        StringBuilder output = null;
        control.AppendBoundButtonNames(ref output, MyGuiInputDeviceEnum.Keyboard);
        MyControl.AppendUnknownTextIfNeeded(ref output, MyTexts.GetString(MyCommonTexts.UnknownControl_None));

        var button = new MyGuiControlButton(
            text: output,
            onButtonClick: OnRebindClick,
            onSecondaryButtonClick: OnUnbindClick,
            toolTip: Description)
        {
            VisualStyle = MyGuiControlButtonStyleEnum.ControlSetting,
            UserData = new ControlButtonData(control, MyGuiInputDeviceEnum.Keyboard),
        };

        return new List<Control>()
        {
            new Control(label, minWidth: Control.LabelMinWidth),
            new Control(button),
            new Control(ctrl, offset: new Vector2(0f, -0.0025f)),
            new Control(alt, offset: new Vector2(0f, -0.0025f)),
            new Control(shift, offset: new Vector2(0f, -0.0025f)),
        };
    }

    public List<Type> SupportedTypes { get; } = new List<Type>()
    {
        typeof(Binding)
    };

    private class ControlButtonData
    {
        public readonly MyControl Control;
        public readonly MyGuiInputDeviceEnum Device;

        public ControlButtonData(MyControl control, MyGuiInputDeviceEnum device)
        {
            Control = control;
            Device = device;
        }
    }

    private void OnRebindClick(MyGuiControlButton button)
    {
        var userData = (ControlButtonData)button.UserData;
        var messageText = MyCommonTexts.AssignControlKeyboard;
        if (userData.Device == MyGuiInputDeviceEnum.Mouse)
            messageText = MyCommonTexts.AssignControlMouse;

        // KEEN!!! MyGuiScreenOptionsMouseKeyboard.MyGuiControlAssignKeyMessageBox is PRIVATE!
        var screenClass = typeof(MyGuiScreenOptionsMouseKeyboard).GetNestedType(
            "MyGuiControlAssignKeyMessageBox",
            BindingFlags.NonPublic);

        var editBindingDialog = (MyGuiScreenBase)Activator.CreateInstance(
            screenClass,
            BindingFlags.CreateInstance,
            null,
            new object[]
            {
                userData.Device,
                userData.Control,
                messageText
            },
            null);

        editBindingDialog.Closed += (s, isUnloading) => StoreControl(button);
        MyGuiSandbox.AddScreen(editBindingDialog);
    }

    private void OnUnbindClick(MyGuiControlButton button)
    {
        void Callback(MyGuiScreenMessageBox.ResultEnum result)
        {
            if (result == MyGuiScreenMessageBox.ResultEnum.NO)
                return;

            var userData = (ControlButtonData)button.UserData;
            userData.Control.SetControl(userData.Device, MyKeys.None);

            StoreControl(button);
        }

        MyGuiScreenBase alert = MyGuiSandbox.CreateMessageBox(
            MyMessageBoxStyleEnum.Info,
            buttonType: MyMessageBoxButtonsType.YES_NO,
            messageText: new StringBuilder("Are you sure?"),
            messageCaption: new StringBuilder("UNBIND CONTROL"),
            yesButtonText: MyStringId.GetOrCompute("Confirm"),
            noButtonText: MyStringId.GetOrCompute("Cancel"),
            callback: Callback
        );

        MyGuiSandbox.AddScreen(alert);
    }

    private void StoreControl(MyGuiControlButton button)
    {
        StringBuilder output = null;
        var userData = (ControlButtonData)button.UserData;
        userData.Control.AppendBoundButtonNames(ref output, userData.Device);

        var binding = propertyGetter();
        binding.Key = userData.Control.GetKeyboardControl();
        propertySetter(binding);

        MyControl.AppendUnknownTextIfNeeded(ref output, MyTexts.GetString(MyCommonTexts.UnknownControl_None));
        button.Text = output.ToString();
        output.Clear();
    }
}