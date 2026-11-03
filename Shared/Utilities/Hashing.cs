using System;
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
            // OpCode.GetHashCode() returns Value on .NET, but hashes the name on Mono
            yield return instruction.opcode.Value;

            var operandHash = HashOperand(instruction.operand);
            if (operandHash.HasValue)
                yield return operandHash.Value;

            foreach (var label in instruction.labels)
                yield return label.GetHashCode();
        }
    }

    // The hashes must come out the same on .NET Framework, Mono and .NET, so the number
    // constants are not hashed with GetHashCode() where the runtimes disagree. The values
    // match .NET's GetHashCode().
    private static int? HashOperand(object operand)
    {
        switch (operand)
        {
            case string s:
                return s.Hash();

            // .NET Framework and Mono: value ^ (value << 8)
            case sbyte value:
                return value;

            // .NET Framework does not normalize NaN
            case float value:
            {
                var bits = BitConverter.ToInt32(BitConverter.GetBytes(value), 0);
                if (((bits - 1) & 0x7FFFFFFF) >= 0x7F800000)
                    bits &= 0x7F800000;
                return bits;
            }

            case double value:
            {
                var bits = BitConverter.DoubleToInt64Bits(value);
                if (((bits - 1) & 0x7FFFFFFFFFFFFFFF) >= 0x7FF0000000000000)
                    bits &= 0x7FF0000000000000;
                return unchecked((int)bits ^ (int)(bits >> 32));
            }

            // byte, int, long and Label hash the same on every runtime
            case ValueType value:
                return value.GetHashCode();

            // Member, type and local operands are left out
            default:
                return null;
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
