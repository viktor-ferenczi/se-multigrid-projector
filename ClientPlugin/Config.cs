using ClientPlugin.Settings;
using ClientPlugin.Settings.Elements;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using MultigridProjector.Config;

namespace ClientPlugin;

public class Config : INotifyPropertyChanged, IPluginConfig
{
    #region Options

    // Core
    private bool showDialogs = true;

    // Compatibility Mode
    private bool clientWelding = true;
    private bool shipWelding = true;
    private bool connectSubgrids = true;

    // Extra Features
    private bool repairProjection = true;
    private bool projectorAligner = true;
    private bool blockHighlight = true;
    private bool craftProjection = true;

    #endregion

    #region User interface

    public readonly string Title = "Multigrid Projector";

    [Separator("Core")]

    [Checkbox(label: "Show Warning Dialogs", description: "Prevent all of Multigrid Projector's warning dialogs from appearing.\nMake sure you've read them before disabling this!")]
    public bool ShowDialogs
    {
        get => showDialogs;
        set => SetField(ref showDialogs, value);
    }

    [Separator("Compatibility Mode")]

    [Checkbox(label: "Client Welding", description: "Place blocks and copy over their properties if they previously could not be welded without the server plugin.")]
    public bool ClientWelding
    {
        get => clientWelding;
        set => SetField(ref clientWelding, value);
    }

    [Checkbox(label: "Ship Welding", description: "Extend the features of client welding to the welders on the grids and subgrids of the craft you are currently piloting.")]
    public bool ShipWelding
    {
        get => shipWelding;
        set => SetField(ref shipWelding, value);
    }

    [Checkbox(label: "Connect Subgrids", description: "Attempt to connect subgrids by removing incorrect heads and placing new ones.")]
    public bool ConnectSubgrids
    {
        get => connectSubgrids;
        set => SetField(ref connectSubgrids, value);
    }

    [Separator("Extra Features")]

    [Checkbox(label: "Repair Projection", description: "Load a copy of a ship into projector so that it can be rebuilt if any accidents happen.")]
    public bool RepairProjection
    {
        get => repairProjection;
        set => SetField(ref repairProjection, value);
    }

    [Checkbox(label: "Align Projection", description: "Enable intuitive alignment of projections using the same keys you would use when aligning blocks normally.")]
    public bool ProjectorAligner
    {
        get => projectorAligner;
        set => SetField(ref projectorAligner, value);
    }

    [Checkbox(label: "Highlight Blocks", description: "Highlight projected blocks based on their status and completion.")]
    public bool BlockHighlight
    {
        get => blockHighlight;
        set => SetField(ref blockHighlight, value);
    }

    [Checkbox(label: "Assemble Projections", description: "View a projection's component cost and queue it for assembly.")]
    public bool CraftProjection
    {
        get => craftProjection;
        set => SetField(ref craftProjection, value);
    }

    #endregion

    #region Shared configuration interface

    // The client always renders preview block visuals. Only the server can disable this for
    // mod compatibility, hence it is not exposed in the client settings dialog.
    public bool PreviewBlockVisuals => true;

    #endregion

    #region Property change notification boilerplate

    public static readonly Config Default = new Config();
    public static readonly Config Current = ConfigStorage.Load();

    public event PropertyChangedEventHandler PropertyChanged;

    protected virtual void OnPropertyChanged(string propertyName)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }

    private bool SetField<T>(ref T field, T value, [CallerMemberName] string propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return false;
        field = value;
        OnPropertyChanged(propertyName);
        return true;
    }

    #endregion
}
