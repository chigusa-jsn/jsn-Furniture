package com.chigusa.jsnfurniture.block;

import com.chigusa.jsnfurniture.JsnFurniture;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.TamableAnimal;
import java.util.List;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/** 椅子やソファに座るための、見えない乗り物 */
public class SeatEntity extends Entity {
    public static final byte SIT = 0;
    public static final byte SWING = 1;
    public static final byte SLIDE = 2;
    private static final net.minecraft.network.syncher.EntityDataAccessor<Byte> MODE =
            SynchedEntityData.defineId(SeatEntity.class, net.minecraft.network.syncher.EntityDataSerializers.BYTE);
    private static final net.minecraft.network.syncher.EntityDataAccessor<BlockPos> ANCHOR =
            SynchedEntityData.defineId(SeatEntity.class, net.minecraft.network.syncher.EntityDataSerializers.BLOCK_POS);
    private static final net.minecraft.network.syncher.EntityDataAccessor<Byte> FACE =
            SynchedEntityData.defineId(SeatEntity.class, net.minecraft.network.syncher.EntityDataSerializers.BYTE);
    private static final net.minecraft.network.syncher.EntityDataAccessor<Integer> START =
            SynchedEntityData.defineId(SeatEntity.class, net.minecraft.network.syncher.EntityDataSerializers.INT);
    /** すべり台：すべり終わるまでの tick */
    private static final int SLIDE_TICKS = 26;
    public SeatEntity(EntityType<? extends SeatEntity> type, Level level) {
        super(type, level);
        noPhysics = true;
    }

    /** pos の家具に座る。height はブロックの下からの高さ（ブロック単位） */
    public static void sit(Level level, BlockPos pos, double height, Player player, Direction facing) {
        if (player.isPassenger()) return;
        AABB box = new AABB(pos);
        if (!level.getEntitiesOfClass(SeatEntity.class, box).isEmpty()) return; // もう誰か座っている
        SeatEntity seat = new SeatEntity(JsnFurniture.SEAT.get(), level);
        seat.setPos(pos.getX() + 0.5, pos.getY() + height, pos.getZ() + 0.5);
        seat.setYRot(facing.toYRot());
        level.addFreshEntity(seat);
        player.startRiding(seat);
        player.setYRot(facing.toYRot());
        player.setYHeadRot(facing.toYRot());
    }

    /**
     * ペット用の家具：リードでつないでいる動物か、近くにいる自分のペットを座らせる。
     * もうだれか座っていたら、降ろす。
     */
    public static void seatPet(Level level, BlockPos pos, double height, Player player, Direction facing) {
        AABB here = new AABB(pos).expandTowards(0, 1, 0);
        List<SeatEntity> seats = level.getEntitiesOfClass(SeatEntity.class, here);
        if (!seats.isEmpty()) {
            for (SeatEntity s : seats) s.ejectPassengers();
            return;
        }
        AABB near = new AABB(pos).inflate(10);
        Mob pet = null;
        for (Mob m : level.getEntitiesOfClass(Mob.class, near, x -> x.getLeashHolder() == player)) {
            pet = m;
            m.dropLeash(true, !player.getAbilities().instabuild);
            break;
        }
        if (pet == null) {
            double best = Double.MAX_VALUE;
            for (TamableAnimal t : level.getEntitiesOfClass(TamableAnimal.class, near, x -> x.isOwnedBy(player) && !x.isPassenger())) {
                double d = t.distanceToSqr(Vec3.atCenterOf(pos));
                if (d < best) {
                    best = d;
                    pet = t;
                }
            }
        }
        if (pet == null) {
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("近くに座らせるペットがいません（リードでつなぐか、自分のペットを近くに連れてきてね）"), true);
            return;
        }
        SeatEntity seat = new SeatEntity(JsnFurniture.SEAT.get(), level);
        seat.setPos(pos.getX() + 0.5, pos.getY() + height, pos.getZ() + 0.5);
        seat.setYRot(facing.toYRot());
        level.addFreshEntity(seat);
        pet.startRiding(seat, true);
        pet.setYRot(facing.toYRot());
        pet.setYBodyRot(facing.toYRot());
        if (pet instanceof TamableAnimal t) t.setOrderedToSit(true);
    }

    @Override
    protected void defineSynchedData(SynchedEntityData.Builder b) {
        b.define(MODE, SIT);
        b.define(ANCHOR, BlockPos.ZERO);
        b.define(FACE, (byte) 2);
        b.define(START, 0);
    }

    /** ブランコの角度（度）。ブランコの絵（AnimRenderer）と同じ式 */
    public static float swingAngle(double time) {
        return (float) Math.sin(time * 0.12) * 32f;
    }

    /** ブランコ・すべり台に乗る */
    public static void ride(Level level, BlockPos pos, Player player, Direction facing, byte mode) {
        if (player.isPassenger()) return;
        if (!level.getEntitiesOfClass(SeatEntity.class, new AABB(pos).inflate(1)).isEmpty()) return;
        SeatEntity seat = new SeatEntity(JsnFurniture.SEAT.get(), level);
        seat.entityData.set(MODE, mode);
        seat.entityData.set(ANCHOR, pos);
        seat.entityData.set(FACE, (byte) facing.get2DDataValue());
        seat.entityData.set(START, (int) level.getGameTime());
        seat.setYRot(facing.toYRot());
        seat.place();
        level.addFreshEntity(seat);
        player.startRiding(seat, true);
        player.setYRot(facing.toYRot());
        if (mode == SLIDE) level.playSound(null, pos, net.minecraft.sounds.SoundEvents.ITEM_PICKUP, net.minecraft.sounds.SoundSource.PLAYERS, 0.5f, 0.6f);
    }

    /** ブランコ・すべり台：時間から今の場所を決める（サーバーと画面で同じ計算） */
    private void place() {
        byte mode = entityData.get(MODE);
        if (mode == SIT) return;
        BlockPos a = entityData.get(ANCHOR);
        Direction f = Direction.from2DDataValue(entityData.get(FACE));
        double fx = f.getStepX(), fz = f.getStepZ();
        double cx = a.getX() + 0.5, cy = a.getY(), cz = a.getZ() + 0.5;
        if (mode == SWING) {
            double ang = Math.toRadians(swingAngle(level().getGameTime()));
            double len = 23.8 / 16.0;
            setPos(cx + fx * len * Math.sin(ang), cy + 30 / 16.0 - len * Math.cos(ang), cz + fz * len * Math.sin(ang));
        } else {
            double t = level().getGameTime() - entityData.get(START);
            double d, y;
            if (t < 8) {
                d = -0.2 + 0.2 * (t / 8.0);
                y = 1.25;
            } else {
                double p = Math.min(1, (t - 8) / (SLIDE_TICKS - 8.0));
                double e = p * p;
                d = 1.15 * e;
                y = 1.25 - 1.1 * e;
            }
            setPos(cx + fx * d, cy + y, cz + fz * d);
        }
    }

    @Override
    protected void readAdditionalSaveData(CompoundTag t) {
    }

    @Override
    protected void addAdditionalSaveData(CompoundTag t) {
    }

    @Override
    public void tick() {
        super.tick();
        byte mode = entityData.get(MODE);
        if (mode != SIT) place();
        if (level().isClientSide) return;
        if (mode == SLIDE && level().getGameTime() - entityData.get(START) >= SLIDE_TICKS) {
            Direction f = Direction.from2DDataValue(entityData.get(FACE));
            for (Entity e : getPassengers()) {
                e.stopRiding();
                e.setDeltaMovement(f.getStepX() * 0.45, 0.05, f.getStepZ() * 0.45);
                e.hurtMarked = true;
            }
            discard();
            return;
        }
        if (mode != SIT) {
            if (getPassengers().isEmpty() || !(level().getBlockState(entityData.get(ANCHOR)).getBlock() instanceof FurnitureBlock)) discard();
            return;
        }
        BlockPos pos = blockPosition();
        boolean onSeat = isSeat(pos) || isSeat(pos.below());
        if (getPassengers().isEmpty() || !onSeat) discard();
    }

    private boolean isSeat(BlockPos p) {
        return level().getBlockState(p).getBlock() instanceof FurnitureBlock f && (f.spec.is("seat") || f.spec.is("pet"));
    }

    @Override
    protected boolean canAddPassenger(Entity e) {
        return getPassengers().isEmpty();
    }

    @Override
    public Vec3 getDismountLocationForPassenger(LivingEntity passenger) {
        if (entityData.get(MODE) == SLIDE) return position();
        if (entityData.get(MODE) == SWING) {
            Direction f = Direction.from2DDataValue(entityData.get(FACE));
            return Vec3.atBottomCenterOf(entityData.get(ANCHOR).relative(f));
        }
        // 前が空いていれば前に、だめなら家具の上に立つ
        BlockPos pos = blockPosition();
        Direction front = Direction.fromYRot(getYRot());
        BlockPos f = pos.relative(front);
        if (level().getBlockState(f).getCollisionShape(level(), f).isEmpty()
                && level().getBlockState(f.above()).getCollisionShape(level(), f.above()).isEmpty()) {
            return Vec3.atBottomCenterOf(f);
        }
        return new Vec3(getX(), pos.getY() + 1.0, getZ());
    }

    @Override
    public boolean isPickable() {
        return false;
    }

    @Override
    public boolean shouldBeSaved() {
        return false;
    }
}
