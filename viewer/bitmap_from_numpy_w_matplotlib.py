#!/usr/bin/env python
#
#  bitmap_from_numpy_w_matplotlib.py
#
#  Copyright (C) 2014 Diamond Light Source
#
#  Author: Luis Fuentes-Montero (Luiso)
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.

from __future__ import division
import wx
import numpy as np
# set backend before importing pyplot
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dials.algorithms.shoebox import MaskCode

class wxbmp_from_np_array(object):

  def __init__(self, lst_data_in, show_nums = True, lst_data_mask_in = None):
    self._ini_wx_bmp_lst = []
    for lst_pos in range(len(lst_data_in)):
      data_3d_in = lst_data_in[lst_pos]
      xmax = data_3d_in.shape[1]
      ymax = data_3d_in.shape[2]
      # remember to put here some assertion to check that
      # both arrays have the same shape

      if(lst_data_mask_in != None):
        data_3d_in_mask = lst_data_mask_in[lst_pos]

      self.vl_max = np.amax(data_3d_in)
      self.vl_min = np.amin(data_3d_in)
      tmp_data2d = np.zeros( (xmax, ymax), 'double')
      tmp_data2d_mask = np.zeros( (xmax, ymax), 'double')
      z_dp = data_3d_in.shape[0]
      single_block_lst_01 = []
      for z in range(z_dp):
        tmp_data2d[:, :] = data_3d_in[z:z + 1, :, :]
        if(lst_data_mask_in != None):
          tmp_data2d_mask[:, :] = data_3d_in_mask[z:z + 1, :, :]
        else:
          tmp_data2d_mask = None
        data_sigle_img = self._wx_img(tmp_data2d, show_nums, tmp_data2d_mask)
        single_block_lst_01.append(data_sigle_img)

      self._ini_wx_bmp_lst.append(single_block_lst_01)


  def bmp_lst_scaled(self, scale = 1.0):
    wx_bmp_lst = []
    for data_3d in self._ini_wx_bmp_lst:
      single_block_lst = []
      for sigle_img_data in data_3d:
        single_block_lst.append(self._wx_bmp_scaled(sigle_img_data, scale))

      wx_bmp_lst.append(single_block_lst)

    return wx_bmp_lst


  def _wx_img(self, np_2d_tmp, show_nums, np_2d_mask = None):

    d = self.vl_max - self.vl_min
    vl_mid_low = self.vl_min + d / 3.0
    vl_mid_hig = self.vl_max - d / 3.0
    log_debug_code = '''
    print
    print "self.vl_min =", self.vl_min
    print " vl_mid_low =", vl_mid_low
    print " vl_mid_hig =", vl_mid_hig
    print "self.vl_max =", self.vl_max
    '''
    lc_fig = plt.figure(frameon=False)

    xmax = np_2d_tmp.shape[0]
    ymax = np_2d_tmp.shape[1]

    lc_fig.set_size_inches(xmax * .5, ymax * .5)

    ax = plt.Axes(lc_fig, [0., 0., 1., 1.])

    ax.set_axis_off()
    lc_fig.add_axes(ax)
    plt.imshow(np.transpose(np_2d_tmp), interpolation = "nearest", cmap = 'hot',
               vmin = self.vl_min, vmax = self.vl_max)

    if( np_2d_mask != None):
      dst_diag = 0.05
      for xpos in range(xmax):
        for ypos in range(ymax):
          loc_mask = int(np_2d_mask[xpos, ypos])

          if( loc_mask != 0 ):

            # drawing box
            plt.vlines(xpos - 0.45, ypos - 0.45, ypos + 0.45,
                       color = 'gray', linewidth=2)
            plt.vlines(xpos + 0.45, ypos - 0.45, ypos + 0.45,
                       color = 'gray', linewidth=2)
            plt.hlines(ypos - 0.45, xpos - 0.45, xpos + 0.45,
                       color = 'gray', linewidth=2)
            plt.hlines(ypos + 0.45, xpos - 0.45, xpos + 0.45,
                       color = 'gray', linewidth=2)

            if( (loc_mask & MaskCode.Background) == MaskCode.Background ):
              # drawing v_lines
              plt.vlines(xpos, ypos - 0.45, ypos + 0.45,
                         color = 'gray', linewidth=2)
              plt.vlines(xpos + 0.225, ypos - 0.45, ypos + 0.45,
                         color = 'gray', linewidth=2)
              plt.vlines(xpos - 0.225, ypos - 0.45, ypos + 0.45,
                         color = 'gray', linewidth=2)

            if( (loc_mask & MaskCode.Foreground) == MaskCode.Foreground ):
              # drawing lines from 1p5 to 7p5
              plt.plot([xpos - dst_diag, xpos - 0.45], [ypos - 0.45, ypos - dst_diag],
                       color='gray', linewidth=2)
              plt.plot([xpos + dst_diag, xpos + 0.45], [ypos + 0.45, ypos + dst_diag],
                       color='gray', linewidth=2)
              plt.plot([xpos - 0.45, xpos + 0.45], [ypos + 0.45, ypos - 0.45],
                       color='gray', linewidth=2)

            if( (loc_mask &  MaskCode.Valid) == MaskCode.Valid ):
              # drawing lines from 4p5 to 10p5
              plt.plot([xpos + dst_diag, xpos - 0.45], [ypos + 0.45, ypos - dst_diag],
                       color='gray', linewidth=2)
              plt.plot([xpos + dst_diag, xpos + 0.45], [ypos - 0.45, ypos - dst_diag],
                       color='gray', linewidth=2)
              plt.plot([xpos + 0.45, xpos - 0.45], [ypos + 0.45, ypos - 0.45],
                       color='gray', linewidth=2)

            if( (loc_mask & MaskCode.BackgroundUsed) == MaskCode.BackgroundUsed ):
              # drawing h_lines
              plt.hlines(ypos , xpos - 0.45, xpos + 0.45,
                         color = 'gray', linewidth=2)
              plt.hlines(ypos + 0.225, xpos - 0.45, xpos + 0.45,
                         color = 'gray', linewidth=2)
              plt.hlines(ypos - 0.225, xpos - 0.45, xpos + 0.45,
                         color = 'gray', linewidth=2)


    if( show_nums != 0 ):
      for xpos in range(xmax):
        for ypos in range(ymax):
          f_num = np_2d_tmp[xpos,ypos]
          g = float("{0:.3f}".format(float(f_num)))

          txt_dat = str(g)
          if( f_num < vl_mid_low ):
            clr_chr = 'yellow'
          elif(f_num > vl_mid_hig):
            clr_chr = 'black'
          else:
            clr_chr = 'blue'

          plt.annotate(txt_dat, xy = (xpos - 0.5, ypos + 0.1), xycoords = 'data',
                       color = clr_chr, size = 9.)


    lc_fig.canvas.draw()
    width, height = lc_fig.canvas.get_width_height()
    np_buf = np.fromstring (lc_fig.canvas.tostring_rgb(), dtype=np.uint8)
    np_buf.shape = (width, height, 3)
    np_buf = np.roll(np_buf, 3, axis = 2)
    self._wx_image = wx.EmptyImage(width, height)
    self._wx_image.SetData(np_buf )
    data_to_become_bmp = (self._wx_image, width, height)

    plt.close(lc_fig)

    return data_to_become_bmp


  def _wx_bmp_scaled(self, data_to_become_bmp, scale):
    to_become_bmp = data_to_become_bmp[0]
    width = data_to_become_bmp[1]
    height = data_to_become_bmp[2]

    NewW = int(width * scale)
    NewH = int(height * scale)
    to_become_bmp = to_become_bmp.Scale(NewW, NewH, wx.IMAGE_QUALITY_NORMAL)
    wxBitmap = to_become_bmp.ConvertToBitmap()
    return wxBitmap
