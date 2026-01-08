using System.Collections.Generic;
using System.Reflection;
using System.Runtime.CompilerServices;
using HarmonyLib;

namespace MultigridProjector.Utilities;

public static class Hashing
{
    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static int Hash(this string value)
    {
        unchecked
        {
            const int offsetBasis = unchecked((int)2166136261);
            const int prime = 16777619;

            var hash = offsetBasis;
            foreach (var t in value)
            {
                hash ^= t;
                hash *= prime;
            }

            return hash;
        }
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static int HashBody(this MethodInfo methodInfo)
    {
        var code = PatchProcessor.GetCurrentInstructions(methodInfo);
        return code.HashInstructions().CombineHashCodes();
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static int HashBody(this ConstructorInfo constructorInfo)
    {
        var code = PatchProcessor.GetCurrentInstructions(constructorInfo);
        return code.HashInstructions().CombineHashCodes();
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static IEnumerable<int> HashInstructions(this IEnumerable<CodeInstruction> instructions)
    {
        foreach (var instruction in instructions)
        {
            yield return instruction.opcode.GetHashCode();

            if (instruction.operand is string s)
                yield return s.Hash();
            else if (instruction.operand != null && instruction.operand.GetType().IsValueType)
                yield return instruction.operand.GetHashCode();

            foreach (var label in instruction.labels)
                yield return label.GetHashCode();
        }
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    public static int CombineHashCodes(this IEnumerable<int> hashCodes)
    {
        // https://stackoverflow.com/questions/1646807/quick-and-simple-hash-code-combinations

        unchecked
        {
            var hash1 = (5381 << 16) + 5381;
            var hash2 = hash1;

            var i = 0;
            foreach (var hashCode in hashCodes)
            {
                if (i % 2 == 0)
                    hash1 = ((hash1 << 5) + hash1 + (hash1 >> 27)) ^ hashCode;
                else
                    hash2 = ((hash2 << 5) + hash2 + (hash2 >> 27)) ^ hashCode;

                ++i;
            }

            return hash1 + hash2 * 1566083941;
        }
    }
}