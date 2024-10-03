# Copyright 2024 The swirl_dynamics Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions for the template."""

import collections
from collections.abc import Callable, Mapping, Sequence
import functools
import os
from typing import Any

import torch
import numpy as np
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter
from tensorboard.backend.event_processing import event_accumulator

Scalar = Any


def primary_process_only(cls: type[Any]) -> type[Any]:
  """Class decorator that modifies all methods to run on primary host only."""

  def wrap_method(method: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
      if torch.distributed.get_rank() == 0:
        return method(self, *args, **kwargs)
      else:
        return None

    return wrapper

  for attr_name, attr_value in cls.__dict__.items():
    if callable(attr_value) and not attr_name.startswith("__"):
      setattr(cls, attr_name, wrap_method(attr_value))

  return cls


def load_scalars_from_tfevents(
    logdir: str,
) -> Mapping[int, Mapping[str, Scalar]]:
  """Loads scalar summaries from events in a logdir."""
  event_acc = event_accumulator.EventAccumulator(logdir)
  event_acc.Reload()

  data = collections.defaultdict(dict)

  for tag in event_acc.Tags()['scalars']:
    for scalar_event in event_acc.Scalars(tag):
      data[scalar_event.step][tag] = scalar_event.value

  return data


def is_scalar(value: Any) -> bool:
  """Checks if a given value is a scalar."""
  if isinstance(value, (int, float, np.number)):
    return True
  if isinstance(value, (np.ndarray, torch.Tensor)):
    return value.ndim == 0 or value.numel() <= 1
  return False


def opt_chain(
    transformations: Sequence[optim.Optimizer],
) -> optim.Optimizer:
  """Wraps `optax.chain` to allow keyword arguments (for gin config)."""
  if len(transformations) == 1:
    return transformations[0]
  else:
    raise NotImplementedError("PyTorch does not support chaining optimizers. Use custom optimizer Logic.")



def create_slice(
    start: int | None = None, end: int | None = None, step: int | None = None
) -> slice:
  """Wraps the python `slice` to allow keyword arguments (for gin config)."""
  return slice(start, end, step)