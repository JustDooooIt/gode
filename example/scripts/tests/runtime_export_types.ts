import type { GDArray, GDDictionary, VariantArgument } from "godot";
import type RuntimeArrayResource from "./runtime_array_resource.js";

export type RuntimeImportedLevel = "alpha" | "beta";
export type RuntimeImportedSingleLevel = "solo" | null;
export type RuntimeImportedResourceArray = Array<RuntimeArrayResource>;
export type RuntimeImportedResourceMap = ReadonlyMap<string, RuntimeArrayResource>;
export type RuntimeImportedGenericArray<T extends VariantArgument> = GDArray<T>;
export type RuntimeImportedGenericDictionary<T extends VariantArgument> = GDDictionary<string, T>;
