# -*- coding: utf-8 -*-
"""
test_roulette_distribution.py

Checks if the vocabulary system actually varies its output (Roulette logic)
when the action intent is broad (e.g. 'fight').
"""
import sys
import random
import unittest
from collections import Counter

import test_bootstrap  # noqa: F401 — パッケージコンテキストを自動解決

import improved_pose_emotion_vocab as garnish_vocab

class TestRouletteDistribution(unittest.TestCase):
    def test_combat_roulette(self):
        # "fight" should trigger roulette
        action_text = "fight"
        seed_base = 1000
        samples = []
        
        # We invoke sample_garnish which internally calls _resolve_micro_actions
        # We need to make sure we parse the results to see if we got different items.
        
        for i in range(200):
            res = garnish_vocab.sample_garnish(
                seed=seed_base + i,
                action_text=action_text,
                max_items=5,
                include_camera=False
            )
            # Flatten list to string for easy counting
            samples.append(" ".join(res))
            
        # Analyze diversity
        # We expect terms like "sword", "bow", "clenched fists", "magic" etc.
        # But note: current implementation might mix things.
        
        text_blob = " ".join(samples).lower()
        
        has_sword = "sword" in text_blob or "blade" in text_blob
        has_bow = "bow" in text_blob or "arrow" in text_blob
        has_fists = "fists" in text_blob or "punch" in text_blob
        has_magic = "magic" in text_blob or "energy" in text_blob or "spell" in text_blob
        
        # We check if we have at least SOME variation.
        # It's possible not ALL appear if probabilities are low, but with 200 samples, likely.
        
        variation_score = sum([has_sword, has_bow, has_fists, has_magic])
        
        print(f"Combat Variation Score: {variation_score}/4 (Sword, Bow, Fists, Magic)")
        
        # At least 2 different types should appear to call it a "Roulette"
        self.assertGreaterEqual(variation_score, 2, "Roulette should produce at least 2 different combat styles")

    def test_performance_roulette(self):
        action_text = "play music"
        seed_base = 2000
        samples = []
        
        for i in range(200):
            res = garnish_vocab.sample_garnish(
                seed=seed_base + i,
                action_text=action_text,
                max_items=5
            )
            samples.append(" ".join(res))
            
        text_blob = " ".join(samples).lower()
        has_guitar = "guitar" in text_blob
        has_piano = "piano" in text_blob or "key" in text_blob
        has_violin = "violin" in text_blob
        has_drum = "drum" in text_blob
        
        variation_score = sum([has_guitar, has_piano, has_violin, has_drum])
        print(f"Performance Variation Score: {variation_score}/4 (Guitar, Piano, Violin, Drum)")
        
        self.assertGreaterEqual(variation_score, 2, "Roulette should produce at least 2 different instruments")

    def test_daily_life_roulette(self):
        # "relaxing" should trigger daily_life roulette with sub-types (reading, drink, care, etc.)
        action_text = "relaxing in room"
        seed_base = 3000
        samples = []
        
        for i in range(200):
            res = garnish_vocab.sample_garnish(
                seed=seed_base + i,
                action_text=action_text,
                max_items=5
            )
            samples.append(" ".join(res))
            
        text_blob = " ".join(samples).lower()
        has_reading = "book" in text_blob or "magazine" in text_blob
        has_drink = "coffee" in text_blob or "tea" in text_blob or "mug" in text_blob
        has_smartphone = "phone" in text_blob or "selfie" in text_blob
        has_care = "mirror" in text_blob or "brushing" in text_blob
        
        variation_score = sum([has_reading, has_drink, has_smartphone, has_care])
        print(f"Daily Life Variation Score: {variation_score}/4 (Reading, Drink, Smartphone, Care)")
        self.assertGreaterEqual(variation_score, 3, "Daily Life Roulette should produce at least 3 different activity types")

    def test_surveillance_roulette(self):
        # "surveillance" should trigger surveillance roulette
        action_text = "surveillance mission"
        seed_base = 4000
        samples = []
        
        for i in range(200):
            res = garnish_vocab.sample_garnish(
                seed=seed_base + i,
                action_text=action_text,
                max_items=5
            )
            samples.append(" ".join(res))
            
        text_blob = " ".join(samples).lower()
        has_camera = "camera" in text_blob
        has_binoc = "binoculars" in text_blob
        has_note = "note" in text_blob
        
        variation_score = sum([has_camera, has_binoc, has_note])
        print(f"Surveillance Variation Score: {variation_score}/3 (Camera, Binoculars, Note)")
        self.assertGreaterEqual(variation_score, 2, "Surveillance Roulette should produce at least 2 different tools")

    def test_nature_relax_roulette(self):
        # "relaxing in nature"
        action_text = "relaxing in nature park"
        seed_base = 5000
        samples = []
        
        for i in range(200):
            res = garnish_vocab.sample_garnish(
                seed=seed_base + i,
                action_text=action_text,
                max_items=5
            )
            samples.append(" ".join(res))
            
        text_blob = " ".join(samples).lower()
        has_flower = "flower" in text_blob
        has_book = "reading" in text_blob or "sketching" in text_blob
        has_nap = "lying" in text_blob or "nap" in text_blob
        
        variation_score = sum([has_flower, has_book, has_nap])
        print(f"Nature Relax Variation Score: {variation_score}/3 (Flower, Book/Sketch, Nap)")
        self.assertGreaterEqual(variation_score, 2, "Nature Relax Roulette should produce at least 2 different activities")

    def test_browsing_shop_roulette(self):
        # NEW: "browsing shop"
        action_text = "browsing shop"
        seed_base = 6000
        samples = []
        
        for i in range(200):
            res = garnish_vocab.sample_garnish(
                seed=seed_base + i,
                action_text=action_text,
                max_items=5
            )
            samples.append(" ".join(res))
            
        text_blob = " ".join(samples).lower()
        has_clock = "clock" in text_blob
        has_jewelry = "jewelry" in text_blob
        has_book = "book" in text_blob
        has_case = "case" in text_blob
        
        variation_score = sum([has_clock, has_jewelry, has_book, has_case])
        print(f"Browsing Shop Variation Score: {variation_score}/4 (Clock, Jewelry, Book, Case)")
        self.assertGreaterEqual(variation_score, 1, "Browsing Shop Roulette should produce at least 1 item type (9-way roulette, ~11% per sub-option)")

    def test_commuter_transit_roulette(self):
        # NEW: "commuter transit"
        action_text = "commuter transit"
        seed_base = 7000
        samples = []
        
        for i in range(200):
            res = garnish_vocab.sample_garnish(
                seed=seed_base + i,
                action_text=action_text,
                max_items=5
            )
            samples.append(" ".join(res))
            
        text_blob = " ".join(samples).lower()
        has_strap = "strap" in text_blob
        has_watch = "watch" in text_blob
        has_phone = "smartphone" in text_blob or "phone" in text_blob
        has_newspaper = "newspaper" in text_blob
        
        variation_score = sum([has_strap, has_watch, has_phone, has_newspaper])
        print(f"Commuter Transit Variation Score: {variation_score}/4 (Strap, Watch, Phone, Newspaper)")
        self.assertGreaterEqual(variation_score, 2, "Commuter Transit Roulette should produce at least 2 different behaviors")

if __name__ == "__main__":
    unittest.main()
