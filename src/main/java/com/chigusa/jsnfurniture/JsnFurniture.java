package com.chigusa.jsnfurniture;

import com.chigusa.jsnfurniture.block.DisplayBlockEntity;
import com.chigusa.jsnfurniture.block.FBedBlock;
import com.chigusa.jsnfurniture.block.FurinBlockEntity;
import com.chigusa.jsnfurniture.block.FurnitureBlock;
import com.chigusa.jsnfurniture.block.SeatEntity;
import com.chigusa.jsnfurniture.block.StorageBlockEntity;
import com.mojang.logging.LogUtils;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.item.BedItem;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.DoubleHighBlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.DoorBlock;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.properties.BlockSetType;
import net.minecraft.world.level.material.PushReaction;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.registries.DeferredBlock;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredItem;
import net.neoforged.neoforge.registries.DeferredRegister;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

/** jsn-Furniture：洋風・和風の家具 */
@Mod(JsnFurniture.MODID)
public class JsnFurniture {
    public static final String MODID = "jsn_furniture";
    public static final Logger LOGGER = LogUtils.getLogger();

    public static final DeferredRegister.Blocks BLOCKS = DeferredRegister.createBlocks(MODID);
    public static final DeferredRegister.Items ITEMS = DeferredRegister.createItems(MODID);
    public static final DeferredRegister<BlockEntityType<?>> BLOCK_ENTITIES = DeferredRegister.create(Registries.BLOCK_ENTITY_TYPE, MODID);
    public static final DeferredRegister<EntityType<?>> ENTITIES = DeferredRegister.create(Registries.ENTITY_TYPE, MODID);
    public static final DeferredRegister<SoundEvent> SOUNDS = DeferredRegister.create(Registries.SOUND_EVENT, MODID);
    public static final DeferredRegister<CreativeModeTab> TABS = DeferredRegister.create(Registries.CREATIVE_MODE_TAB, MODID);

    /** 家具 id → ブロック */
    public static final Map<String, DeferredBlock<FurnitureBlock>> FURNITURE = new LinkedHashMap<>();
    public static final Map<String, DeferredItem<? extends Item>> ITEM_BY_ID = new LinkedHashMap<>();
    private static final Map<String, List<String>> TAB_ITEMS = new LinkedHashMap<>();

    public static final Map<String, DeferredHolder<SoundEvent, SoundEvent>> SOUND = new LinkedHashMap<>();

    static {
        for (String s : new String[]{"furin_glass", "furin_iron", "furin_bamboo", "furin_ceramic", "furin_brass", "shishi_odoshi"}) {
            SOUND.put(s, SOUNDS.register(s, () -> SoundEvent.createVariableRangeEvent(ResourceLocation.fromNamespaceAndPath(MODID, s))));
        }
        for (Spec s : Spec.ALL) {
            DeferredBlock<FurnitureBlock> b = BLOCKS.register(s.id(), () -> new FurnitureBlock(s, props(s)));
            FURNITURE.put(s.id(), b);
            ITEM_BY_ID.put(s.id(), ITEMS.registerSimpleBlockItem(b));
            TAB_ITEMS.computeIfAbsent(s.tab(), k -> new ArrayList<>()).add(s.id());
        }
        for (Spec.Bed bed : Spec.BEDS) {
            DeferredBlock<FBedBlock> b = BLOCKS.register(bed.id(), () -> new FBedBlock(bed.futon(), BlockBehaviour.Properties.of()
                    .sound(bed.futon() ? SoundType.WOOL : SoundType.WOOD).strength(0.4f).noOcclusion().pushReaction(PushReaction.DESTROY)));
            ITEM_BY_ID.put(bed.id(), ITEMS.register(bed.id(), () -> new BedItem(b.get(), new Item.Properties().stacksTo(1))));
            TAB_ITEMS.computeIfAbsent(bed.tab(), k -> new ArrayList<>()).add(bed.id());
        }
        for (Spec.Door door : Spec.DOORS) {
            DeferredBlock<DoorBlock> b = BLOCKS.register(door.id(), () -> new DoorBlock(BlockSetType.BAMBOO,
                    BlockBehaviour.Properties.of().sound(SoundType.BAMBOO_WOOD).strength(1.5f).noOcclusion().pushReaction(PushReaction.DESTROY)));
            ITEM_BY_ID.put(door.id(), ITEMS.register(door.id(), () -> new DoubleHighBlockItem(b.get(), new Item.Properties())));
            TAB_ITEMS.computeIfAbsent("wa", k -> new ArrayList<>()).add(door.id());
        }
    }

    public static final Supplier<BlockEntityType<StorageBlockEntity>> STORAGE_BE = BLOCK_ENTITIES.register("storage",
            () -> BlockEntityType.Builder.of(StorageBlockEntity::new, blocksOf("storage")).build(null));
    public static final Supplier<BlockEntityType<DisplayBlockEntity>> DISPLAY_BE = BLOCK_ENTITIES.register("display",
            () -> BlockEntityType.Builder.of(DisplayBlockEntity::new, blocksOf("display")).build(null));
    public static final Supplier<BlockEntityType<FurinBlockEntity>> FURIN_BE = BLOCK_ENTITIES.register("furin",
            () -> BlockEntityType.Builder.of(FurinBlockEntity::new, blocksOf("furin")).build(null));

    public static final Supplier<EntityType<SeatEntity>> SEAT = ENTITIES.register("seat",
            () -> EntityType.Builder.<SeatEntity>of(SeatEntity::new, MobCategory.MISC).sized(0.001f, 0.001f).noSummon()
                    .clientTrackingRange(10).updateInterval(20).build("seat"));

    static {
        tab("west", "chair");
        tab("wa", "furin_red");
    }

    private static void tab(String key, String iconSuffix) {
        TABS.register(key, () -> CreativeModeTab.builder()
                .title(Component.translatable("itemGroup." + MODID + "." + key))
                .icon(() -> {
                    String icon = key.equals("west") ? "oak_chair" : "furin_red";
                    return ITEM_BY_ID.get(icon).get().getDefaultInstance();
                })
                .displayItems((params, out) -> {
                    for (String id : TAB_ITEMS.getOrDefault(key, List.of())) out.accept(ITEM_BY_ID.get(id).get());
                }).build());
    }

    private static Block[] blocksOf(String kind) {
        List<Block> list = new ArrayList<>();
        for (Spec s : Spec.ALL) if (s.is(kind)) list.add(FURNITURE.get(s.id()).get());
        return list.toArray(new Block[0]);
    }

    private static BlockBehaviour.Properties props(Spec s) {
        BlockBehaviour.Properties p = BlockBehaviour.Properties.of().sound(switch (s.sound()) {
            case "wool" -> SoundType.WOOL;
            case "stone" -> SoundType.STONE;
            case "metal" -> SoundType.METAL;
            case "glass" -> SoundType.GLASS;
            case "bamboo" -> SoundType.BAMBOO_WOOD;
            case "grass" -> SoundType.GRASS;
            default -> SoundType.WOOD;
        }).strength(s.tool().equals("pickaxe") ? 2.0f : 1.5f, 6f);
        if (!s.full()) p = p.noOcclusion().isViewBlocking((st, l, pos) -> false).isSuffocating((st, l, pos) -> false);
        if (s.passable()) p = p.noCollission();
        int light = s.light();
        if (light > 0) {
            boolean toggles = s.is("lamp");
            p = p.lightLevel(st -> !toggles || (st.hasProperty(FurnitureBlock.LIT) && st.getValue(FurnitureBlock.LIT)) ? light : 0);
        }
        if (s.tall()) p = p.pushReaction(PushReaction.DESTROY);
        return p;
    }

    public JsnFurniture(IEventBus bus) {
        BLOCKS.register(bus);
        ITEMS.register(bus);
        BLOCK_ENTITIES.register(bus);
        ENTITIES.register(bus);
        SOUNDS.register(bus);
        TABS.register(bus);
    }
}
