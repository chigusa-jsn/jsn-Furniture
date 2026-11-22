package com.chigusa.jsnfurniture.client;

import com.chigusa.jsnfurniture.block.DisplayBlockEntity;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.client.renderer.blockentity.BlockEntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.world.item.ItemDisplayContext;

/** ショーケースの中のアイテムを、くるくる回して見せる */
public class DisplayRenderer implements BlockEntityRenderer<DisplayBlockEntity> {
    public DisplayRenderer(BlockEntityRendererProvider.Context ctx) {
    }

    @Override
    public void render(DisplayBlockEntity be, float partial, PoseStack pose, MultiBufferSource buffers, int light, int overlay) {
        if (be.item.isEmpty() || be.getLevel() == null) return;
        float t = be.getLevel().getGameTime() + partial;
        pose.pushPose();
        pose.translate(0.5, 0.55 + Math.sin(t / 20.0) * 0.03, 0.5);
        pose.mulPose(Axis.YP.rotationDegrees(t * 2f));
        pose.scale(0.55f, 0.55f, 0.55f);
        Minecraft.getInstance().getItemRenderer().renderStatic(be.item, ItemDisplayContext.FIXED, light, OverlayTexture.NO_OVERLAY,
                pose, buffers, be.getLevel(), 0);
        pose.popPose();
    }
}
