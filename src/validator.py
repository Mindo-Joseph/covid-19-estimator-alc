# This class validates the keys and values

class Validator:
    @staticmethod
    def check_empty_values(**formdict):
        """ Check if the json value is empty"""
        for value in formdict.values():
            if not value:
                return False
        return True

    @staticmethod
    def check_keys(**formdict):
        """ check if json key exists """
        if all([formkey for formkey in formdict]):
            return True
        return False
    @staticmethod
    def check_valid_keys(*requiredKeys,**formdict):
        """ check for the valid keys in dict """
        if all([requiredKey in formdict.keys()] for requiredKey in requiredKeys):
            return True
        return False
    @staticmethod
    def check_valid_string(*formStrings):
        for formString in formStrings:
            if formString != str:
                return False
        return True
    @staticmethod    
    def check_valid_integer(*formInts):
        for formInt in formInts:
            if formInt != int:
                return False
        return True
        
    @staticmethod
    def checkAbsoluteSpaceCharacters(*fromStrings):

        """ A method to check if values are space characters """

        for fromString in fromStrings:
            if fromString.isspace():
                return True
        return False
        

        
        