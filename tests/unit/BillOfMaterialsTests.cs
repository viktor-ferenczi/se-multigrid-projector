using System.Collections.Generic;
using MultigridProjectorClient.Extra;
using Xunit;

public class BillOfMaterialsTests
{
    private static readonly KeyValuePair<string, int>[] Items =
    {
        new KeyValuePair<string, int>("MyObjectBuilder_Component/SteelPlate", 1250),
        new KeyValuePair<string, int>("MyObjectBuilder_Component/Construction", 300),
        new KeyValuePair<string, int>("MyObjectBuilder_Component/Thrust", 0),
    };

    [Fact]
    public void Isy()
    {
        Assert.Equal(
            "Component/Construction=300\nComponent/SteelPlate=1250",
            BillOfMaterials.Format(BomFormat.Isy, Items)
        );
    }

    [Fact]
    public void Goat()
    {
        Assert.Equal(
            "@GOAT-Stock Definitions START\nConstructionComp=300\nSteelPlate=1250\n@GOAT-Stock Definitions END",
            BillOfMaterials.Format(BomFormat.GOAT, Items)
        );
    }

    [Fact]
    public void GoatEmpty()
    {
        Assert.Equal(
            "@GOAT-Stock Definitions START\n@GOAT-Stock Definitions END",
            BillOfMaterials.Format(BomFormat.GOAT, new KeyValuePair<string, int>[0])
        );
    }

    // GOAT Sorter 1.3.0's default item names, from its item class and its table of vanilla items
    [Theory]
    [InlineData("MyObjectBuilder_Component/SteelPlate", "SteelPlate")]
    [InlineData("MyObjectBuilder_Component/BulletproofGlass", "BulletproofGlass")]
    [InlineData("MyObjectBuilder_Component/Construction", "ConstructionComp")]
    [InlineData("MyObjectBuilder_Component/Detector", "DetectorComponent")]
    [InlineData("MyObjectBuilder_Component/GravityGenerator", "GravityGenComponent")]
    [InlineData("MyObjectBuilder_Component/Medical", "MedicalComponent")]
    [InlineData("MyObjectBuilder_Component/RadioCommunication", "RadioCommComponent")]
    [InlineData("MyObjectBuilder_Component/Reactor", "ReactorComponent")]
    [InlineData("MyObjectBuilder_Component/Thrust", "ThrustComponent")]
    [InlineData("MyObjectBuilder_Component/PrototechFrame", "PrototechFrame")]
    [InlineData("MyObjectBuilder_Component/SomeModdedPart", "SomeModdedPart")]
    [InlineData("MyObjectBuilder_Ore/Iron", "IronOre")]
    [InlineData("MyObjectBuilder_Ore/Scrap", "Scrap")]
    [InlineData("MyObjectBuilder_Ingot/Iron", "IronIngot")]
    [InlineData("MyObjectBuilder_SeedItem/Fruit", "FruitSeed")]
    [InlineData("MyObjectBuilder_ConsumableItem/MealPack_Ramen", "Ramen")]
    [InlineData("Component/SteelPlate", "SteelPlate")]
    public void GoatName(string id, string name)
    {
        Assert.Equal(name, BillOfMaterials.GoatName(id));
    }
}
