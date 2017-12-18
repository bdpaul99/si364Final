import requests
import json
from mixoligist import get_drinks, get_drink_by_name


import unittest

class TestAPIMethods(unittest.TestCase):
    def test_bad_ingredient(self):
        error_string = "Sorry, there were no drinks found with those ingredients"

        self.assertEqual(get_drinks(['asdfadsff']), error_string)
    
    def test_return_type_get_drinks(self):
        self.assertEqual(type(get_drinks(['Rum'])),type([]))
    
    def test_return_number_get_drinks(self):
        self.assertTrue(len(get_drinks(['vodka'])) > 1)

    def test_return_number_get_drinks_multiple_ingredients(self):
        self.assertTrue(len(get_drinks(['vodka', 'orange juice'])) > 1)

    def test_return_type_get_drink_by_name(self):
        self.assertEqual(type(get_drink_by_name('Tom Collins')), tuple)
    def test_result_get_drink_by_name(self):
        self.assertEqual(get_drink_by_name('Tom Collins')[0], 'Tom Collins')
    def test_result_get_drink_by_name2(self):
        self.assertEqual(type(get_drink_by_name('Tom Collins')[1]), type([]))
    def test_result_get_drink_by_name3(self):
        tom_collins_instructions = 'In a shaker half-filled with ice cubes, combine the gin, lemon juice, and sugar. Shake well. Strain into a collins glass alomst filled with ice cubes. Add the club soda. Stir and garnish with the cherry and the orange slice.'
        self.assertEqual(get_drink_by_name('Tom Collins')[2],tom_collins_instructions)    





unittest.main()
