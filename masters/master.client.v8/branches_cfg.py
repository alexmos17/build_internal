# -*- python -*-
# ex: set syntax=python:

# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This file defines the current branches that we test on the v8 waterfall.
# Note that stable and beta might not always correspond to what is used in
# Chromium, but here we simple use it to mean the last 2 branches.

stable_branch = '3.19'
beta_branch = '3.20'
branch_names = {
    'stable': {'ia32': 'V8 Linux - ' + stable_branch + ' branch',
               'arm': 'V8 arm - sim - ' + stable_branch + ' branch',
               'x64': 'V8 Linux64 - ' + stable_branch + ' branch'},
    'beta': {'ia32': 'V8 Linux - ' + beta_branch + ' branch',
             'arm': 'V8 arm - sim - ' + beta_branch + ' branch',
             'x64': 'V8 Linux64 - ' + beta_branch + ' branch'}}
