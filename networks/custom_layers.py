import torch
from torch import nn
import torch.nn.functional as F


    
# Pixelwise feature vector normalization.
# reference:
# https://github.com/tkarras/progressive_growing_of_gans/blob/master/networks.py#L120
class PixelwiseNorm(nn.Module):
    def __init__(self):
        super(PixelwiseNorm, self).__init__()

    
    def forward(self, x, alpha=1e-8):
        y = x.pow(2.).mean(dim=1, keepdim=True).add(alpha).sqrt()
        y = x / y # normalize input x
        return y
        


"""
Code from: https://github.com/akanimax/BMSG-GAN/blob/master/sourcecode/MSG_GAN/CustomLayers.py
"""
# Layers required for Building The generator and
# discriminator
class GenInitialBlock(nn.Module):
    """
    Module implementing the initial block of the Generator
    Takes in whatever latent size and generates output volume
    of size 4 x 4
    """

    def __init__(self, in_channels):
        super().__init__()

        self.fc1 = nn.Linear(in_channels, in_channels)
        self.fc2 = nn.Linear(in_channels, in_channels)

        self.tr_conv = nn.ConvTranspose2d(in_channels, in_channels, (4, 4), bias=True) 
        self.conv = nn.Conv2d(in_channels, in_channels, (3, 3), padding=(1, 1), bias=True)

        self.lrelu = nn.LeakyReLU(0.2)

        self.pixel_norm = PixelwiseNorm()


    def forward(self, x):
        y = self.lrelu(self.fc1(x))
        y = self.lrelu(self.fc2(y))
        y = y.view(*y.shape, 1, 1) 
        y = self.lrelu(self.tr_conv(y))
        y = self.lrelu(self.conv(y))
        y = self.pixel_norm(y)

        return y


class GenGeneralConvBlock(nn.Module):
    """ Module implementing a general convolutional block """

    def __init__(self, in_channels, out_channels):
        super().__init__()

        self.conv_1 = nn.Conv2d(in_channels, out_channels, (3, 3), padding=(1, 1), bias=True)
        self.conv_2 = nn.Conv2d(out_channels, out_channels, (3, 3), padding=(1, 1), bias=True)

        self.pixel_norm = PixelwiseNorm()

        self.lrelu = nn.LeakyReLU(0.2)


    def forward(self, x):
        y = F.interpolate(x, scale_factor=2) # Upsample
        y = self.pixel_norm(self.lrelu(self.conv_1(y)))
        y = self.pixel_norm(self.lrelu(self.conv_2(y)))

        return y



class MinibatchStdDev(nn.Module):
    """
    Minibatch standard deviation layer for the discriminator
    """

    def __init__(self):
        super().__init__()

    
    def forward(self, x, alpha=1e-8):
        batch_size, _, height, width = x.shape

        # [B x C x H x W] Subtract mean over batch.
        y = x - x.mean(dim=0, keepdim=True)

        # [1 x C x H x W]  Calc standard deviation over batch
        y  = torch.sqrt(y.pow(2.).mean(dim=0, keepdim=False) + alpha)

        # [1]  Take average over feature_maps and pixels.
        y = y.mean().view(1, 1, 1, 1)

        # [B x 1 x H x W]  Replicate over group and pixels.
        y = y.repeat(batch_size, 1, height, width)

        # [B x C x H x W]  Append as new feature_map.
        y = torch.cat([x, y], 1)

        # return computed values
        return y



class DisFinalBlock(nn.Module):
    """ Final block for the Discriminator """

    def __init__(self, out_channels):
        super().__init__()

        self.batch_discriminator = MinibatchStdDev()

        # 1 from batch_discriminator, 3 from rbg generator image concat
        in_channels = out_channels + 1 + 3

        self.conv_1 = nn.Conv2d(in_channels, out_channels, (3, 3), padding=(1, 1), bias=True)
        self.conv_2 = nn.Conv2d(out_channels, out_channels, (4, 4), bias=True)

        # final conv layer emulates a fully connected layer
        self.conv_3 = nn.Conv2d(out_channels, 1, (1, 1), bias=True)

        self.lrelu = nn.LeakyReLU(0.2)


    def forward(self, x):
        # print(f"OUTPUT SIZE: {x.size()}")
        y = self.batch_discriminator(x)
        # print(f"OUTPUT SIZE: {y.size()}")
        y = self.lrelu(self.conv_1(y))
        # print(f"OUTPUT SIZE conv1 final: {x.size()}")
        y = self.lrelu(self.conv_2(y))
        # print(f"OUTPUT SIZE conv2 final: {x.size()}")
        # fully connected layer
        y = self.conv_3(y)  # This layer has linear activation
        # print(f"OUTPUT SIZE conv3 final: {x.size()}")
        # flatten the output raw discriminator scores
        return y.view(-1)



class DisGeneralConvBlock(nn.Module):
    """ General block in the discriminator """

    def __init__(self, out1_channels, out2_channels, first_layer=False):
        super().__init__()

        # self.batch_discriminator = MinibatchStdDev()

        # 1 from batch_discriminator, 3 from rbg generator image concat
        in_channels = out1_channels # + 1
        if not first_layer:
            in_channels += 3


        self.conv_1 = nn.Conv2d(in_channels, out1_channels, (3, 3), padding=1, bias=True)
        self.conv_2 = nn.Conv2d(out1_channels, out2_channels, (3, 3), padding=1, bias=True)

        self.down_sampler = nn.AvgPool2d(2)

        self.lrelu = nn.LeakyReLU(0.2)


    def forward(self, x):
        # print(f"OUTPUT SIZE: {x.size()}")
        # y = self.batch_discriminator(x)
        # print(f"OUTPUT SIZE conv1 general: {y.size()}")
        y = self.lrelu(self.conv_1(x))
        # print(f"OUTPUT SIZE conv1 general: {x.size()}")
        y = self.lrelu(self.conv_2(y))
        # print(f"OUTPUT SIZE conv 2 general: {x.size()}")
        y = self.down_sampler(y)
        # print(f"OUTPUT SIZE sample general: {x.size()}")

        return y