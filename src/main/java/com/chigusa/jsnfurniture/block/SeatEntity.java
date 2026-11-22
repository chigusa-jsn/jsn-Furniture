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
        if (level().isClientSide) return;
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
