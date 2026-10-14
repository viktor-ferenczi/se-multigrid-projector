using System.Collections.Generic;
using System.Linq;

namespace MultigridProjectorClient.Extra
{
    // Inventory manager scripts the Copy BoM button can format the bill of materials for
    public enum BomFormat
    {
        Isy,
        GOAT,
    }

    // Formats a bill of materials for the stock containers of inventory manager scripts.
    // Items are given by their definition id, like MyObjectBuilder_Component/SteelPlate.
    public static class BillOfMaterials
    {
        private const string IdPrefix = "MyObjectBuilder_";

        // GOAT Sorter's own names for the vanilla components whose name is not their subtype
        private static readonly Dictionary<string, string> GoatComponentNames = new()
        {
            { "Construction", "ConstructionComp" },
            { "Detector", "DetectorComponent" },
            { "GravityGenerator", "GravityGenComponent" },
            { "Medical", "MedicalComponent" },
            { "RadioCommunication", "RadioCommComponent" },
            { "Reactor", "ReactorComponent" },
            { "Thrust", "ThrustComponent" },
        };

        // Items with a zero amount are left out, both scripts default to zero
        public static string Format(BomFormat format, IEnumerable<KeyValuePair<string, int>> items)
        {
            items = items.Where(item => item.Value > 0);
            switch (format)
            {
                case BomFormat.GOAT:
                    return FormatGoat(items);
                default:
                    return FormatIsy(items);
            }
        }

        // Isy's Inventory Manager: one Type/Subtype=amount line per item, pasted into the
        // custom data of a container with Special in its name
        private static string FormatIsy(IEnumerable<KeyValuePair<string, int>> items)
        {
            var lines = items
                .Select(item => $"{StripPrefix(item.Key)}={item.Value}")
                .OrderBy(line => line, System.StringComparer.Ordinal);

            return string.Join("\n", lines);
        }

        // GOAT Sorter: Name=amount lines between the stock definition markers, pasted into the
        // custom data of a container tagged [Stock]. The script reads nothing outside the
        // markers and adds the items not listed with a zero amount.
        private static string FormatGoat(IEnumerable<KeyValuePair<string, int>> items)
        {
            var lines = items
                .Select(item => $"{GoatName(item.Key)}={item.Value}")
                .OrderBy(line => line, System.StringComparer.Ordinal)
                .Prepend("@GOAT-Stock Definitions START")
                .Append("@GOAT-Stock Definitions END");

            return string.Join("\n", lines);
        }

        // The item name GOAT Sorter defaults to, unless the player renamed the item in the
        // custom data of the script's programmable block
        public static string GoatName(string id)
        {
            string[] parts = StripPrefix(id).Split(new[] { '/' }, 2);
            if (parts.Length != 2)
                return id;

            string type = parts[0];
            string subtype = parts[1];

            switch (type)
            {
                case "Component":
                    return GoatComponentNames.TryGetValue(subtype, out string name)
                        ? name
                        : subtype;
                case "Ore":
                    return subtype.Contains("Scrap") ? subtype : subtype + "Ore";
                case "Ingot":
                    return subtype + "Ingot";
                case "SeedItem":
                    return subtype + "Seed";
                default:
                    return subtype.Replace("MealPack_", "");
            }
        }

        private static string StripPrefix(string id)
        {
            return id.StartsWith(IdPrefix) ? id.Substring(IdPrefix.Length) : id;
        }
    }
}
