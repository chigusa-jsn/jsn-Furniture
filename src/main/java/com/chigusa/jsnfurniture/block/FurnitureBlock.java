package com.chigusa.jsnfurniture.block;

import com.chigusa.jsnfurniture.JsnFurniture;
import com.chigusa.jsnfurniture.Spec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.Containers;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.ItemUtils;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.alchemy.PotionContents;
import net.minecraft.world.item.alchemy.Potions;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.EntityBlock;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.level.block.state.properties.DirectionProperty;
import net.minecraft.world.level.block.state.properties.DoubleBlockHalf;
import net.minecraft.world.level.block.state.properties.EnumProperty;
import net.minecraft.world.level.pathfinder.PathComputationType;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;
import org.jetbrains.annotations.Nullable;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 家具ブロック（ほとんど全部これ1つ）。何ができるかは Spec の kind で決まる。
 * ・seat：右クリックで座る ・storage：物を入れる ・lamp：つける／消す ・curtain：開け閉め
 * ・display：アイテムを1つ飾る ・furin：風鈴 ・shishi：鹿威し ・sink：水をくむ
 * tall なら2マスの高さ（下が本体）。
 */
public class FurnitureBlock extends Block implements EntityBlock {
    public static final DirectionProperty FACING = BlockStateProperties.HORIZONTAL_FACING;
    public static final BooleanProperty LIT = BlockStateProperties.LIT;
    public static final BooleanProperty OPEN = BlockStateProperties.OPEN;
    public static final EnumProperty<DoubleBlockHalf> HALF = BlockStateProperties.DOUBLE_BLOCK_HALF;
    public static final BooleanProperty TILT = BooleanProperty.create("tilt");

    /** ブロックの状態の種類は親のコンストラクタの中で決まるので、そのあいだ Spec をここに置いておく */
    private static final ThreadLocal<Spec> BUILDING = new ThreadLocal<>();

    public final Spec spec;
    private final Map<String, VoxelShape> shapes = new HashMap<>();

    public FurnitureBlock(Spec spec, Properties props) {
        super(begin(spec, props));
        this.spec = spec;
        BUILDING.remove();
        BlockState d = stateDefinition.any().setValue(FACING, Direction.NORTH);
        if (d.hasProperty(LIT)) d = d.setValue(LIT, false);
        if (d.hasProperty(OPEN)) d = d.setValue(OPEN, false);
        if (d.hasProperty(HALF)) d = d.setValue(HALF, DoubleBlockHalf.LOWER);
        if (d.hasProperty(TILT)) d = d.setValue(TILT, false);
        registerDefaultState(d);
    }

    private static Properties begin(Spec spec, Properties props) {
        BUILDING.set(spec);
        return props;
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> b) {
        Spec s = BUILDING.get();
        b.add(FACING);
        if (s == null) return;
        if (s.is("lamp")) b.add(LIT);
        if (s.is("curtain")) b.add(OPEN);
        if (s.tall()) b.add(HALF);
        if (s.is("shishi")) b.add(TILT);
    }

    private boolean upper(BlockState st) {
        return st.hasProperty(HALF) && st.getValue(HALF) == DoubleBlockHalf.UPPER;
    }

    // ------------------------------------------------------------------ 形

    @Override
    protected VoxelShape getShape(BlockState st, BlockGetter level, BlockPos pos, CollisionContext ctx) {
        Direction f = st.getValue(FACING);
        boolean up = upper(st);
        boolean open = st.hasProperty(OPEN) && st.getValue(OPEN);
        String key = f + "/" + up + "/" + open;
        return shapes.computeIfAbsent(key, k -> build(open && !spec.openShape().isEmpty() ? spec.openShape() : spec.shape(), f, up));
    }

    @Override
    protected VoxelShape getCollisionShape(BlockState st, BlockGetter level, BlockPos pos, CollisionContext ctx) {
        return spec.passable() ? Shapes.empty() : getShape(st, level, pos, ctx);
    }

    @Override
    protected boolean isPathfindable(BlockState st, PathComputationType type) {
        return spec.passable();
    }

    private static VoxelShape build(List<double[]> boxes, Direction f, boolean upper) {
        VoxelShape out = Shapes.empty();
        for (double[] b : boxes) {
            double y1 = b[1], y2 = b[4];
            if (upper) {
                y1 = Math.max(0, y1 - 16);
                y2 = y2 - 16;
            } else {
                y2 = Math.min(16, y2);
            }
            if (y2 <= y1) continue;
            double x1 = b[0], z1 = b[2], x2 = b[3], z2 = b[5];
            double[] r = switch (f) {
                case EAST -> new double[]{16 - z2, x1, 16 - z1, x2};
                case SOUTH -> new double[]{16 - x2, 16 - z2, 16 - x1, 16 - z1};
                case WEST -> new double[]{z1, 16 - x2, z2, 16 - x1};
                default -> new double[]{x1, z1, x2, z2};
            };
            if (r[2] <= r[0] || r[3] <= r[1]) continue;
            out = Shapes.or(out, Block.box(r[0], y1, r[1], r[2], y2, r[3]));
        }
        return out.isEmpty() ? Block.box(6, 0, 6, 10, 2, 10) : out.optimize();
    }

    // ------------------------------------------------------------------ 置く・壊す

    @Nullable
    @Override
    public BlockState getStateForPlacement(BlockPlaceContext ctx) {
        Direction face = ctx.getClickedFace();
        Direction facing = spec.wall() && face.getAxis().isHorizontal() ? face : ctx.getHorizontalDirection().getOpposite();
        BlockPos pos = ctx.getClickedPos();
        if (spec.tall()) {
            if (pos.getY() >= ctx.getLevel().getMaxBuildHeight() - 1 || !ctx.getLevel().getBlockState(pos.above()).canBeReplaced(ctx)) {
                return null;
            }
        }
        return defaultBlockState().setValue(FACING, facing);
    }

    @Override
    public void setPlacedBy(Level level, BlockPos pos, BlockState st, @Nullable LivingEntity by, ItemStack stack) {
        if (spec.tall()) level.setBlock(pos.above(), st.setValue(HALF, DoubleBlockHalf.UPPER), 3);
    }

    @Override
    protected BlockState updateShape(BlockState st, Direction dir, BlockState other, LevelAccessor level, BlockPos pos, BlockPos otherPos) {
        if (spec.tall() && dir.getAxis() == Direction.Axis.Y) {
            boolean up = upper(st);
            if ((dir == Direction.UP) == !up) {
                boolean ok = other.is(this) && other.getValue(HALF) != st.getValue(HALF);
                if (!ok) return Blocks.AIR.defaultBlockState();
            }
        }
        return super.updateShape(st, dir, other, level, pos, otherPos);
    }

    @Override
    public BlockState playerWillDestroy(Level level, BlockPos pos, BlockState st, Player player) {
        // クリエイティブで上を壊したとき、下からアイテムが出ないように
        if (!level.isClientSide && spec.tall() && upper(st) && player.isCreative()) {
            BlockPos below = pos.below();
            BlockState b = level.getBlockState(below);
            if (b.is(this) && !upper(b)) {
                level.setBlock(below, Blocks.AIR.defaultBlockState(), 35);
                level.levelEvent(player, 2001, below, Block.getId(b));
            }
        }
        return super.playerWillDestroy(level, pos, st, player);
    }

    @Override
    protected void onRemove(BlockState st, Level level, BlockPos pos, BlockState now, boolean moved) {
        if (!st.is(now.getBlock())) {
            BlockEntity be = level.getBlockEntity(pos);
            if (be instanceof StorageBlockEntity s) {
                Containers.dropContents(level, pos, s);
            } else if (be instanceof DisplayBlockEntity d && !d.item.isEmpty()) {
                Containers.dropItemStack(level, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, d.item);
            }
        }
        super.onRemove(st, level, pos, now, moved);
    }

    @Override
    protected BlockState rotate(BlockState st, Rotation rot) {
        return st.setValue(FACING, rot.rotate(st.getValue(FACING)));
    }

    @Override
    protected BlockState mirror(BlockState st, Mirror mirror) {
        return st.rotate(mirror.getRotation(st.getValue(FACING)));
    }

    // ------------------------------------------------------------------ さわる

    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState st, Level level, BlockPos pos, Player player,
                                              InteractionHand hand, BlockHitResult hit) {
        if (spec.is("display")) {
            if (!(level.getBlockEntity(pos) instanceof DisplayBlockEntity d)) return ItemInteractionResult.FAIL;
            if (d.item.isEmpty() && !stack.isEmpty()) {
                if (!level.isClientSide) {
                    d.setItem(stack.copyWithCount(1));
                    if (!player.getAbilities().instabuild) stack.shrink(1);
                    level.playSound(null, pos, SoundEvents.ITEM_FRAME_ADD_ITEM, SoundSource.BLOCKS, 1f, 1f);
                }
                return ItemInteractionResult.sidedSuccess(level.isClientSide);
            }
            return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        }
        if (spec.is("sink")) {
            ItemStack result = null;
            if (stack.is(Items.BUCKET)) result = new ItemStack(Items.WATER_BUCKET);
            else if (stack.is(Items.GLASS_BOTTLE)) result = PotionContents.createItemStack(Items.POTION, Potions.WATER);
            if (result != null) {
                if (!level.isClientSide) {
                    player.setItemInHand(hand, ItemUtils.createFilledResult(stack, player, result));
                    level.playSound(null, pos, stack.is(Items.BUCKET) ? SoundEvents.BUCKET_FILL : SoundEvents.BOTTLE_FILL, SoundSource.BLOCKS, 1f, 1f);
                }
                return ItemInteractionResult.sidedSuccess(level.isClientSide);
            }
        }
        return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState st, Level level, BlockPos pos, Player player, BlockHitResult hit) {
        if (upper(st)) {
            // 2マスの家具は、下の本体を操作する
            BlockPos below = pos.below();
            BlockState b = level.getBlockState(below);
            if (!b.is(this)) return InteractionResult.PASS;
            pos = below;
            st = b;
        }
        switch (spec.kind()) {
            case "seat" -> {
                if (player.isShiftKeyDown()) return InteractionResult.PASS;
                if (!level.isClientSide) SeatEntity.sit(level, pos, spec.seat() / 16.0, player, st.getValue(FACING));
                return InteractionResult.sidedSuccess(level.isClientSide);
            }
            case "pet" -> {
                if (!level.isClientSide) SeatEntity.seatPet(level, pos, spec.seat() / 16.0, player, st.getValue(FACING));
                return InteractionResult.sidedSuccess(level.isClientSide);
            }
            case "storage" -> {
                if (!level.isClientSide && level.getBlockEntity(pos) instanceof StorageBlockEntity s) {
                    player.openMenu(s);
                    level.playSound(null, pos, SoundEvents.BARREL_OPEN, SoundSource.BLOCKS, 0.5f, 1.1f);
                }
                return InteractionResult.sidedSuccess(level.isClientSide);
            }
            case "lamp" -> {
                if (!level.isClientSide) {
                    boolean on = !st.getValue(LIT);
                    level.setBlock(pos, st.setValue(LIT, on), 3);
                    if (spec.tall()) {
                        BlockState above = level.getBlockState(pos.above());
                        if (above.is(this)) level.setBlock(pos.above(), above.setValue(LIT, on), 3);
                    }
                    SoundEvent s = spec.particles().contains("flame") ? (on ? SoundEvents.FLINTANDSTEEL_USE : SoundEvents.FIRE_EXTINGUISH)
                            : SoundEvents.STONE_BUTTON_CLICK_ON;
                    level.playSound(null, pos, s, SoundSource.BLOCKS, 0.5f, on ? 1.2f : 0.9f);
                }
                return InteractionResult.sidedSuccess(level.isClientSide);
            }
            case "curtain" -> {
                if (!level.isClientSide) {
                    boolean open = !st.getValue(OPEN);
                    level.setBlock(pos, st.setValue(OPEN, open), 3);
                    level.playSound(null, pos, spec.sound().equals("bamboo") ? SoundEvents.BAMBOO_WOOD_TRAPDOOR_OPEN : SoundEvents.WOOL_PLACE,
                            SoundSource.BLOCKS, 0.8f, open ? 1.1f : 0.9f);
                }
                return InteractionResult.sidedSuccess(level.isClientSide);
            }
            case "display" -> {
                if (level.getBlockEntity(pos) instanceof DisplayBlockEntity d && !d.item.isEmpty()) {
                    if (!level.isClientSide) {
                        ItemStack it = d.item;
                        d.setItem(ItemStack.EMPTY);
                        if (!player.addItem(it)) player.drop(it, false);
                        level.playSound(null, pos, SoundEvents.ITEM_FRAME_REMOVE_ITEM, SoundSource.BLOCKS, 1f, 1f);
                    }
                    return InteractionResult.sidedSuccess(level.isClientSide);
                }
                return InteractionResult.PASS;
            }
            case "furin" -> {
                if (!level.isClientSide) {
                    playFurin(level, pos, 1.0f);
                    level.blockEvent(pos, this, 1, 0);
                }
                return InteractionResult.sidedSuccess(level.isClientSide);
            }
            default -> {
                return InteractionResult.PASS;
            }
        }
    }

    @Override
    protected boolean triggerEvent(BlockState st, Level level, BlockPos pos, int id, int param) {
        super.triggerEvent(st, level, pos, id, param);
        BlockEntity be = level.getBlockEntity(pos);
        return be != null && be.triggerEvent(id, param);
    }

    // ------------------------------------------------------------------ 音・動き

    public void playFurin(Level level, BlockPos pos, float volume) {
        var s = JsnFurniture.SOUND.get("furin_" + spec.furin());
        if (s == null) return;
        float pitch = 0.94f + level.random.nextFloat() * 0.12f;
        if (level.isClientSide) {
            level.playLocalSound(pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, s.get(), SoundSource.BLOCKS, volume, pitch, false);
        } else {
            level.playSound(null, pos, s.get(), SoundSource.BLOCKS, volume, pitch);
        }
    }

    @Override
    public void animateTick(BlockState st, Level level, BlockPos pos, RandomSource r) {
        if (spec.is("furin")) {
            // 風でときどき鳴る（雨や雷のときはよく鳴る）
            int chance = level.isThundering() ? 2 : level.isRaining() ? 4 : 9;
            if (r.nextInt(chance) == 0) {
                playFurin(level, pos, 0.35f + r.nextFloat() * 0.25f);
                if (level.getBlockEntity(pos) instanceof FurinBlockEntity f) f.ring(level.getGameTime(), 0.6f);
            }
            return;
        }
        if (st.hasProperty(LIT) && st.getValue(LIT) && !upper(st)) {
            String p = spec.particles();
            if (p.contains("flame") && r.nextInt(2) == 0) {
                level.addParticle(ParticleTypes.SMALL_FLAME, pos.getX() + 0.3 + r.nextDouble() * 0.4, pos.getY() + (spec.id().equals("stove") ? 1.0 : 0.35),
                        pos.getZ() + 0.3 + r.nextDouble() * 0.4, 0, 0.01, 0);
            }
            if (p.contains("smoke") && r.nextInt(3) == 0) {
                level.addParticle(ParticleTypes.CAMPFIRE_COSY_SMOKE, pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5, 0, 0.04, 0);
            }
        }
    }

    // 鹿威し：水がたまるとカコンと鳴る（ずっとくり返す）
    @Override
    protected void onPlace(BlockState st, Level level, BlockPos pos, BlockState old, boolean moved) {
        if (spec.is("shishi") && !level.isClientSide && !old.is(this)) level.scheduleTick(pos, this, 80 + level.random.nextInt(60));
    }

    @Override
    protected void tick(BlockState st, ServerLevel level, BlockPos pos, RandomSource r) {
        if (!spec.is("shishi")) return;
        if (!st.getValue(TILT)) {
            level.setBlock(pos, st.setValue(TILT, true), 3);
            var s = JsnFurniture.SOUND.get("shishi_odoshi");
            level.playSound(null, pos, s.get(), SoundSource.BLOCKS, 1.0f, 0.95f + r.nextFloat() * 0.1f);
            level.sendParticles(ParticleTypes.SPLASH, pos.getX() + 0.5, pos.getY() + 0.3, pos.getZ() + 0.5, 8, 0.2, 0.05, 0.2, 0.1);
            level.scheduleTick(pos, this, 14);
        } else {
            level.setBlock(pos, st.setValue(TILT, false), 3);
            level.scheduleTick(pos, this, 140 + r.nextInt(80));
        }
    }

    // ------------------------------------------------------------------ ブロックエンティティ

    @Nullable
    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState st) {
        if (upper(st)) return null;
        return switch (spec.kind()) {
            case "storage" -> new StorageBlockEntity(pos, st);
            case "display" -> new DisplayBlockEntity(pos, st);
            case "furin" -> new FurinBlockEntity(pos, st);
            default -> null;
        };
    }

    @Nullable
    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState st, BlockEntityType<T> type) {
        return null;
    }
}
